import os
from pathlib import Path

from app.core.config import settings
from app.core.security import decrypt_text, encrypt_text
from app.models import AuditLog, FabricAnalysis
from tests.conftest import PASSWORD, hdr, image_bytes, new_client, register, upload


# ---------------- CSRF
def test_csrf_required_for_state_changes(user_client):
    r = user_client.post("/api/settings/password", json={"current_password": "a", "new_password": "b"})
    assert r.status_code == 403
    r = user_client.put("/api/settings/profile", json={"name": "x"}, headers={"X-CSRF-Token": "forged"})
    assert r.status_code == 403
    assert user_client.put("/api/settings/profile", json={"name": "ok"}, headers=hdr(user_client)).status_code == 200


def test_csrf_required_on_login_and_logout(client):
    assert client.post("/api/auth/login", json={"email": "a@b.co", "password": "x"}).status_code == 403
    assert client.post("/api/auth/logout").status_code == 403


def test_csrf_token_from_other_session_rejected(two_users):
    a, b = two_users
    token_b = b.get("/api/auth/csrf").json()["csrf_token"]
    assert a.put("/api/settings/profile", json={"name": "x"}, headers={"X-CSRF-Token": token_b}).status_code == 403


def test_tampered_session_cookie_rejected(user_client):
    user_client.cookies.set("fsl_session", "tampered.value.here")
    assert user_client.get("/api/auth/me").status_code == 401


# ---------------- authorization / user isolation
def test_cross_user_access_denied(two_users):
    a, b = two_users
    r = upload(a, image_bytes("silk"))
    assert r.status_code == 201
    aid = r.json()["id"]
    assert a.get(f"/api/fabric/{aid}").status_code == 200
    # user B can neither read, view the image, get recommendations, nor delete it
    assert b.get(f"/api/fabric/{aid}").status_code == 404
    assert b.get(f"/api/fabric/{aid}/image").status_code == 404
    assert b.get(f"/api/recommendations/analysis/{aid}").status_code == 404
    assert b.delete(f"/api/fabric/{aid}", headers=hdr(b)).status_code == 404
    assert b.post("/api/recommendations/select", json={"analysis_id": aid, "mode": "Gentle"}, headers=hdr(b)).status_code == 404
    assert a.get(f"/api/fabric/{aid}").status_code == 200  # still there


def test_history_and_analytics_are_isolated(two_users):
    a, b = two_users
    upload(a, image_bytes("wool"))
    assert a.get("/api/history").json()["total"] == 1
    assert b.get("/api/history").json()["total"] == 0
    assert b.get("/api/analytics/summary").json()["total"] == 0
    assert b.get("/api/ml/predictions").json() == []


def test_audit_log_endpoint_only_returns_own_events(two_users):
    a, b = two_users
    upload(a, image_bytes())
    mine = {e["action"] for e in a.get("/api/security/audit").json()}
    theirs = {e["action"] for e in b.get("/api/security/audit").json()}
    assert "image_upload" in mine and "image_upload" not in theirs


def test_endpoints_require_authentication(client):
    for path in ["/api/history", "/api/analytics/summary", "/api/ml/info", "/api/etl/report",
                 "/api/security/controls", "/api/settings", "/api/fabric/1"]:
        assert client.get(path).status_code == 401, path


def test_pages_redirect_when_logged_out(client):
    for path in ["/dashboard", "/history", "/settings", "/analysis/1"]:
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"].startswith("/login")


# ---------------- XSS
def test_xss_in_name_is_escaped_in_html(client):
    register(client, name="<script>alert(1)</script>")
    html = client.get("/dashboard").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_xss_note_round_trips_as_data_not_markup(user_client):
    payload = "<img src=x onerror=alert(1)>"
    r = upload(user_client, image_bytes(), note=payload)
    assert r.status_code == 201
    got = user_client.get(f"/api/fabric/{r.json()['id']}")
    assert got.headers["content-type"].startswith("application/json")
    assert got.json()["note"] == payload  # returned as JSON string; UI inserts via textContent


def test_frontend_never_uses_innerhtml():
    js = (Path(__file__).parents[1] / "app/static/js/app.js").read_text()
    assert "innerHTML" not in js and "document.write" not in js and "eval(" not in js


# ---------------- file validation
def test_rejects_non_image_with_image_extension(user_client):
    r = upload(user_client, b"this is plain text, not an image", "evil.jpg")
    assert r.status_code == 400


def test_rejects_wrong_extension(user_client):
    assert upload(user_client, image_bytes(), "fabric.gif", "image/gif").status_code == 400
    assert upload(user_client, image_bytes(), "fabric.exe", "application/octet-stream").status_code == 400


def test_rejects_empty_and_tiny_and_oversized(user_client):
    assert upload(user_client, b"", "a.jpg").status_code == 400
    assert upload(user_client, image_bytes(size=16), "tiny.jpg").status_code == 400
    big = image_bytes() + b"\0" * (settings.max_upload_mb * 1024 * 1024)
    assert upload(user_client, big, "big.jpg").status_code == 400


def test_rejects_corrupt_image(user_client):
    data = image_bytes()
    assert upload(user_client, data[: len(data) // 3] + b"garbage", "broken.jpg").status_code in (400, 201)
    assert upload(user_client, b"\xff\xd8\xff\xe0" + b"junk" * 10, "broken2.jpg").status_code == 400


def test_filename_is_never_trusted(user_client, db):
    r = upload(user_client, image_bytes(), "../../etc/passwd.jpg")
    assert r.status_code == 201
    a = db.get(FabricAnalysis, r.json()["id"])
    assert ".." not in a.image_path and "passwd" not in a.image_path
    stored = (Path(settings.upload_dir) / a.image_path).resolve()
    assert Path(settings.upload_dir).resolve() in stored.parents and stored.is_file()


def test_png_and_webp_accepted(user_client):
    assert upload(user_client, image_bytes(fmt="PNG"), "a.png", "image/png").status_code == 201
    assert upload(user_client, image_bytes(fmt="WEBP"), "a.webp", "image/webp").status_code == 201


def test_upload_rate_limit(user_client):
    data = image_bytes()
    codes = [upload(user_client, data).status_code for _ in range(22)]
    assert codes.count(429) >= 1


# ---------------- encryption + headers + audit
def test_fernet_round_trip_and_ciphertext_in_db(user_client, db):
    assert decrypt_text(encrypt_text("secret note")) == "secret note"
    assert encrypt_text("secret note") != "secret note"
    r = upload(user_client, image_bytes(), note="my private note")
    a = db.get(FabricAnalysis, r.json()["id"])
    assert a.note_encrypted and "my private note" not in a.note_encrypted
    assert user_client.get(f"/api/fabric/{a.id}").json()["note"] == "my private note"


def test_security_headers_present(client):
    r = client.get("/")
    h = {k.lower(): v for k, v in r.headers.items()}
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "default-src 'self'" in h["content-security-policy"] and "unsafe-inline" not in h["content-security-policy"]
    assert "referrer-policy" in h


def test_no_secrets_in_security_endpoint(user_client):
    text = user_client.get("/api/security/controls").text
    assert os.environ["SECRET_KEY"] not in text and os.environ["FERNET_KEY"] not in text


def test_audit_events_recorded(user_client, db):
    upload(user_client, image_bytes())
    user_client.put("/api/settings/profile", json={"name": "New"}, headers=hdr(user_client))
    actions = {a.action for a in db.query(AuditLog).all()}
    assert {"image_upload", "prediction", "settings_change"} <= actions


def test_data_deletion_removes_files_and_logs(user_client, db):
    r = upload(user_client, image_bytes())
    a = db.get(FabricAnalysis, r.json()["id"])
    path = Path(settings.upload_dir) / a.image_path
    assert path.exists()
    assert user_client.delete("/api/settings/data", headers=hdr(user_client)).json()["deleted"] == 1
    assert not path.exists()
    assert db.query(AuditLog).filter_by(action="data_deletion").count() >= 1
