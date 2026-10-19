"""Deterministic SYNTHETIC DEMO DATA generator (fixed seed). Not real users, not real analyses."""
import json
import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.security import hash_password
from app.models import FabricAnalysis, User, WashingHistory
from app.services.recommendation import load_rules, recommend

SEED = 42
DEMO_USERS = [("Demo User A (Synthetic)", "demo@fabric-demo.local", 150),
              ("Demo User B (Synthetic)", "demo2@fabric-demo.local", 40)]
WEIGHTS = {"cotton": 24, "polyester": 16, "denim": 12, "silk": 8, "wool": 9, "linen": 8,
           "nylon": 6, "rayon": 6, "velvet": 3, "blended": 8}


def seed_demo(db: Session, reset: bool = False) -> dict:
    rng = random.Random(SEED)
    rules = load_rules()
    fabrics, weights = list(WEIGHTS), list(WEIGHTS.values())
    now = utcnow()
    created = {}
    for name, email, n in DEMO_USERS:
        existing = db.query(User).filter_by(email=email).first()
        if existing and not reset:
            created[email] = "exists"
            continue
        if existing:
            db.delete(existing)
            db.commit()
        user = User(name=name, email=email, password_hash=hash_password(settings.demo_password), is_demo=True)
        db.add(user)
        db.commit()
        for _ in range(n):
            fabric = rng.choices(fabrics, weights)[0]
            conf = min(0.99, max(0.42, rng.betavariate(6, 1.6)))
            rec = recommend(fabric, conf, {"has_dryer": rng.random() < 0.6})
            others = [f for f in fabrics if f != fabric]
            top = {fabric: round(conf, 4)}
            rest = 1 - conf
            alt = rng.choice(others)
            top[alt] = round(rest * 0.7, 4)
            a = FabricAnalysis(
                user_id=user.id, image_path="synthetic://demo", predicted_fabric=fabric, confidence=conf,
                washing_temperature=rec["temperature"], washing_mode=f"{rec['wash_mode']} – {rec['washing_method']}",
                drying_method=rec["drying_method"], ironing_temperature=rec["ironing_temperature"],
                special_care=rec["special_care"], low_confidence=rec["low_confidence"],
                probabilities=json.dumps(top), model_version="synthetic-demo", is_synthetic=True,
                created_at=now - timedelta(days=rng.randint(0, 179), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)))
            db.add(a)
            db.flush()
            if rng.random() < 0.6:
                db.add(WashingHistory(user_id=user.id, fabric_analysis_id=a.id,
                                      selected_washing_mode=rng.choice(rules[fabric]["wash_modes"]),
                                      created_at=a.created_at + timedelta(minutes=5)))
        db.commit()
        created[email] = f"created ({n} synthetic analyses)"
    return created


if __name__ == "__main__":
    import argparse

    from app.core.database import SessionLocal, init_db

    ap = argparse.ArgumentParser(description="Load SYNTHETIC demo data")
    ap.add_argument("--reset", action="store_true", help="recreate the demo users")
    args = ap.parse_args()
    init_db()
    with SessionLocal() as s:
        print(seed_demo(s, args.reset))
    print(f"Demo login: demo@fabric-demo.local / {settings.demo_password}  (Synthetic Demo Data)")
