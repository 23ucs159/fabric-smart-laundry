from app.models import FabricAnalysis, User, WashingHistory
from app.services.seed import seed_demo
from tests.conftest import hdr, image_bytes, new_client, register, upload


def test_full_analysis_flow(user_client):
    r = upload(user_client, image_bytes("denim"), has_dryer="false", prefer_gentle="true", note="blue jeans")
    assert r.status_code == 201, r.text
    a = r.json()
    rec = a["recommendation"]
    assert a["predicted_fabric"] and 0 <= a["confidence"] <= 1 and rec["explanation"]
    assert rec["preferences_applied"] == {"has_dryer": False, "prefer_gentle": True}
    assert user_client.get(f"/api/fabric/{a['id']}/image").headers["content-type"] == "image/jpeg"
    got = user_client.get(f"/api/fabric/{a['id']}").json()
    assert got["note"] == "blue jeans" and got["recommendation"]["washing_method"]
    hist = user_client.get("/api/history").json()
    assert hist["total"] == 1 and hist["items"][0]["id"] == a["id"]


def test_history_filter_and_pagination(user_client):
    for f in ["silk", "silk", "wool"]:
        upload(user_client, image_bytes(f, seed=hash(f) % 100))
    allh = user_client.get("/api/history").json()
    assert allh["total"] == 3
    key = allh["items"][0]["fabric_key"]
    flt = user_client.get(f"/api/history?fabric={key}").json()
    assert flt["total"] == sum(1 for i in allh["items"] if i["fabric_key"] == key)
    assert user_client.get("/api/history?page_size=2").json()["pages"] == 2


def test_analytics_uses_real_rows(user_client):
    for f in ["cotton", "cotton", "silk"]:
        upload(user_client, image_bytes(f))
    s = user_client.get("/api/analytics/summary").json()
    assert s["total"] == 3 and sum(s["distribution"]["values"]) == 3 and s["avg_confidence"] > 0
    c = user_client.get("/api/analytics/charts").json()
    assert sum(c["confidence"]["values"]) == 3 and sum(c["temperature"]["values"]) == 3
    assert len(c["frequency"]["labels"]) == 30 and sum(c["frequency"]["values"]) == 3
    assert c["most_common"] and c["most_common"][0]["count"] >= 1


def test_wash_mode_selection(user_client, db):
    a = upload(user_client, image_bytes("wool")).json()
    mode = a["recommendation"]["wash_modes"][0]
    assert user_client.post("/api/recommendations/select", json={"analysis_id": a["id"], "mode": mode}, headers=hdr(user_client)).status_code == 201
    assert user_client.post("/api/recommendations/select", json={"analysis_id": a["id"], "mode": "Boil"}, headers=hdr(user_client)).status_code == 400
    assert db.query(WashingHistory).filter_by(fabric_analysis_id=a["id"]).count() == 1
    assert user_client.get("/api/recommendations/selections").json()[0]["mode"] == mode


def test_recommendation_lookup_endpoint(user_client):
    r = user_client.get("/api/recommendations/lookup?fabric=silk&has_dryer=true").json()
    assert r["fabric"] == "silk" and "Do not tumble dry" in r["drying_method"]
    assert user_client.get("/api/recommendations/lookup?fabric=banana").status_code == 404
    assert len(user_client.get("/api/recommendations/fabrics").json()) == 10


def test_delete_analysis(user_client):
    a = upload(user_client, image_bytes()).json()
    assert user_client.delete(f"/api/fabric/{a['id']}", headers=hdr(user_client)).status_code == 200
    assert user_client.get(f"/api/fabric/{a['id']}").status_code == 404


def test_settings_profile_password_preferences(user_client):
    h = lambda: hdr(user_client)
    assert user_client.put("/api/settings/profile", json={"name": "New Name"}, headers=h()).json()["name"] == "New Name"
    assert user_client.put("/api/settings/preferences", json={"theme": "dark", "notifications_enabled": False}, headers=h()).status_code == 200
    assert user_client.put("/api/settings/preferences", json={"theme": "neon", "notifications_enabled": True}, headers=h()).status_code == 422
    s = user_client.get("/api/settings").json()
    assert s["theme"] == "dark" and s["notifications_enabled"] is False and any(f["status"] == "future" for f in s["features"])
    assert user_client.post("/api/settings/password", json={"current_password": "wrong", "new_password": "Newpass123"}, headers=h()).status_code == 400
    assert user_client.post("/api/settings/password", json={"current_password": user_client.password, "new_password": "weak"}, headers=h()).status_code == 400
    assert user_client.post("/api/settings/password", json={"current_password": user_client.password, "new_password": "Newpass123"}, headers=h()).status_code == 200
    c2 = new_client()
    assert c2.post("/api/auth/login", json={"email": user_client.email, "password": "Newpass123"}, headers=hdr(c2)).status_code == 200
    assert "data-theme=\"dark\"" in user_client.get("/dashboard").text


def test_etl_endpoints(user_client):
    assert user_client.get("/api/etl/report").status_code == 200
    r = user_client.post("/api/etl/run?source=messy", headers=hdr(user_client)).json()
    assert r["records"]["invalid"] == 11
    assert user_client.get("/api/etl/report").json()["records"]["total"] == 17
    assert user_client.post("/api/etl/run?source=../../etc/passwd", headers=hdr(user_client)).status_code == 400
    user_client.post("/api/etl/run?source=baseline", headers=hdr(user_client))


def test_ml_info_endpoint(user_client):
    m = user_client.get("/api/ml/info").json()
    assert m["available"] and m["test"]["confusion_matrix"] and m["limitations"] and m["dataset"]["source"]


def test_security_controls_endpoint(user_client):
    names = {c["name"] for c in user_client.get("/api/security/controls").json()["controls"]}
    assert {"Password hashing", "CSRF protection", "Rate limiting", "Field encryption", "Audit logging"} <= names


def test_openapi_docs_available(client):
    assert client.get("/api/docs").status_code == 200 and client.get("/api/redoc").status_code == 200
    paths = client.get("/api/openapi.json").json()["paths"]
    assert "/api/fabric/analyze" in paths and "/api/assistant/ask" in paths


def test_seed_is_deterministic_and_labelled(db):
    from app.core.database import SessionLocal
    seed_demo(db, reset=True)
    first = [(a.predicted_fabric, round(a.confidence, 6)) for a in
             db.query(FabricAnalysis).join(User).filter(User.email == "demo@fabric-demo.local").order_by(FabricAnalysis.id)]
    seed_demo(db, reset=True)
    second = [(a.predicted_fabric, round(a.confidence, 6)) for a in
              db.query(FabricAnalysis).join(User).filter(User.email == "demo@fabric-demo.local").order_by(FabricAnalysis.id)]
    assert first == second and len(first) == 150
    u = db.query(User).filter_by(email="demo@fabric-demo.local").one()
    assert u.is_demo and "Synthetic" in u.name and all(a.is_synthetic for a in u.analyses)


def test_demo_user_dashboard_shows_synthetic_flag(db):
    seed_demo(db)
    c = new_client()
    r = c.post("/api/auth/login", json={"email": "demo@fabric-demo.local", "password": "DemoPass2026"}, headers=hdr(c))
    assert r.status_code == 200
    s = c.get("/api/analytics/summary").json()
    assert s["total"] == 150 and s["synthetic_count"] == 150
    assert c.get("/api/history").json()["items"][0]["is_synthetic"] is True
    b = new_client(); register(b)
    assert b.get("/api/analytics/summary").json()["total"] == 0  # demo data never leaks to real users
