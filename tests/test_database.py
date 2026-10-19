import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models import AuditLog, FabricAnalysis, FabricKnowledge, User, WashingHistory
from app.services.recommendation import fabric_keys


def make_user(db, email="dbtest@test.local"):
    u = User(name="DB Test", email=email, password_hash=hash_password("Passw0rd123"))
    db.add(u); db.commit()
    return u


def make_analysis(db, user, fabric="cotton"):
    a = FabricAnalysis(user_id=user.id, image_path="x/y.jpg", predicted_fabric=fabric, confidence=0.9,
                       washing_temperature="30–40°C", washing_mode="Normal", drying_method="Air dry",
                       ironing_temperature="Medium", special_care="none")
    db.add(a); db.commit()
    return a


def test_user_crud(db):
    u = make_user(db, "crud@test.local")
    assert u.id and u.created_at and u.last_login is None
    u.name = "Renamed"; db.commit()
    assert db.get(User, u.id).name == "Renamed"
    db.delete(u); db.commit()
    assert db.get(User, u.id) is None


def test_unique_email(db):
    make_user(db, "dup@test.local")
    with pytest.raises(IntegrityError):
        make_user(db, "dup@test.local")
    db.rollback()


def test_relationships_and_cascade(db):
    u = make_user(db, "rel@test.local")
    a = make_analysis(db, u)
    db.add(WashingHistory(user_id=u.id, fabric_analysis_id=a.id, selected_washing_mode="Gentle")); db.commit()
    db.refresh(u)
    assert len(u.analyses) == 1 and len(u.washing_history) == 1 and a.washing_history[0].analysis is a
    db.delete(a); db.commit()
    assert db.query(WashingHistory).filter_by(user_id=u.id).count() == 0
    db.expire_all()
    db.delete(db.get(User, u.id)); db.commit()


def test_foreign_key_enforced(db):
    db.add(FabricAnalysis(user_id=999999, image_path="a", predicted_fabric="cotton", confidence=.5, washing_temperature="a",
                          washing_mode="a", drying_method="a", ironing_temperature="a", special_care="a"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_audit_log_survives_user_deletion(db):
    u = make_user(db, "audit@test.local")
    db.add(AuditLog(user_id=u.id, action="login", status="success", ip_address="127.0.0.1")); db.commit()
    db.delete(u); db.commit()
    log = db.query(AuditLog).filter_by(action="login", ip_address="127.0.0.1").first()
    assert log is not None and log.user_id is None


def test_knowledge_table_synced_with_rules(db):
    rows = {r.fabric_type: r for r in db.query(FabricKnowledge).all()}
    assert set(fabric_keys()) <= set(rows)
    assert rows["silk"].temperature.startswith("Cold") and rows["wool"].drying_method == "Dry flat"
    assert rows["cotton"].washing_method
