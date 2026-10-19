from app.core.security import hash_password, verify_password
from app.models import AuditLog, User
from tests.conftest import PASSWORD, hdr, new_client, register


def test_register_login_logout_flow(client, db):
    email, pw = register(client, name="Anjali")
    assert client.get("/api/auth/me").json()["email"] == email
    r = client.post("/api/auth/logout", headers=hdr(client))
    assert r.status_code == 200
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401
    r = client.post("/api/auth/login", json={"email": email, "password": pw}, headers=hdr(client))
    assert r.status_code == 200 and r.json()["user"]["name"] == "Anjali"
    actions = {a.action for a in db.query(AuditLog).all()}
    assert {"register", "login", "logout"} <= actions


def test_password_is_argon2_hashed(client, db):
    email, _ = register(client)
    u = db.query(User).filter_by(email=email).one()
    assert u.password_hash.startswith("$argon2")
    assert PASSWORD not in u.password_hash
    assert verify_password(u.password_hash, PASSWORD) and not verify_password(u.password_hash, "wrong")


def test_hash_is_salted():
    assert hash_password("Passw0rd123") != hash_password("Passw0rd123")


def test_invalid_password_rejected_and_audited(client, db):
    email, _ = register(client)
    c2 = new_client()
    r = c2.post("/api/auth/login", json={"email": email, "password": "WrongPass999"}, headers=hdr(c2))
    assert r.status_code == 401
    assert "Invalid email or password" in r.json()["detail"]
    assert db.query(AuditLog).filter_by(action="login", status="failed").count() >= 1


def test_unknown_email_same_error(client):
    r = client.post("/api/auth/login", json={"email": "nobody@test.local", "password": "Whatever123"}, headers=hdr(client))
    assert r.status_code == 401 and r.json()["detail"] == "Invalid email or password."


def test_weak_password_rejected(client):
    for pw in ["short1", "alllettersnodigits", "12345678901"]:
        r = client.post("/api/auth/register", json={"name": "X", "email": "weak@test.local", "password": pw}, headers=hdr(client))
        assert r.status_code == 400


def test_duplicate_email_conflict(client):
    email, _ = register(client)
    c2 = new_client()
    r = c2.post("/api/auth/register", json={"name": "Y", "email": email.upper(), "password": PASSWORD}, headers=hdr(c2))
    assert r.status_code == 409


def test_invalid_email_rejected(client):
    r = client.post("/api/auth/register", json={"name": "Y", "email": "not-an-email", "password": PASSWORD}, headers=hdr(client))
    assert r.status_code == 422


def test_session_cookie_flags(client):
    r = client.post("/api/auth/register", json={"name": "Z", "email": "flags@test.local", "password": PASSWORD}, headers=hdr(client))
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_login_rate_limit(client):
    h = hdr(client)
    codes = [client.post("/api/auth/login", json={"email": "x@test.local", "password": "Nope12345"}, headers=h).status_code
             for _ in range(12)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
    r = client.post("/api/auth/login", json={"email": "x@test.local", "password": "Nope12345"}, headers=h)
    assert "retry-after" in {k.lower() for k in r.headers}


def test_register_rate_limit(client):
    codes = []
    for i in range(7):
        c = new_client()  # same IP ("testclient"), fresh session each time
        codes.append(c.post("/api/auth/register", json={"name": "n", "email": f"rl{i}@test.local", "password": PASSWORD},
                            headers=hdr(c)).status_code)
    assert codes[:5] == [201] * 5 and codes[5] == 429


def test_session_rotates_on_login(client):
    email, pw = register(client)
    before = client.get("/api/auth/csrf").json()["csrf_token"]
    client.post("/api/auth/login", json={"email": email, "password": pw}, headers={"X-CSRF-Token": before})
    assert client.get("/api/auth/csrf").json()["csrf_token"] != before
