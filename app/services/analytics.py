"""Per-user analytics computed from real database rows."""
import json
from collections import Counter
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.models import FabricAnalysis
from app.services.recommendation import load_rules

CONF_BUCKETS = [(0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 101)]


def iso(dt) -> str:
    return dt.isoformat(timespec="seconds") + "Z"


def serialize_analysis(a: FabricAnalysis, decrypt=None) -> dict:
    rules = load_rules()
    meta = rules.get(a.predicted_fabric, {})
    return {
        "id": a.id,
        "created_at": iso(a.created_at),
        "fabric_key": a.predicted_fabric,
        "predicted_fabric": meta.get("display", a.predicted_fabric),
        "confidence": round(a.confidence, 4),
        "low_confidence": a.low_confidence,
        "washing_temperature": a.washing_temperature,
        "washing_mode": a.washing_mode,
        "drying_method": a.drying_method,
        "ironing_temperature": a.ironing_temperature,
        "special_care": a.special_care,
        "is_synthetic": a.is_synthetic,
        "model_version": a.model_version,
        "has_image": not a.image_path.startswith("synthetic://"),
    }


def _rows(db: Session, user_id: int) -> list[FabricAnalysis]:
    return db.query(FabricAnalysis).filter(FabricAnalysis.user_id == user_id).order_by(FabricAnalysis.created_at).all()


def month_label(dt) -> str:
    return dt.strftime("%Y-%m")


def summary(db: Session, user_id: int) -> dict:
    rows = _rows(db, user_id)
    rules = load_rules()
    total = len(rows)
    counts = Counter(r.predicted_fabric for r in rows)
    most = counts.most_common(1)[0][0] if counts else None
    months = Counter(month_label(r.created_at) for r in rows)
    return {
        "total": total,
        "most_detected": rules[most]["display"] if most else None,
        "avg_confidence": round(sum(r.confidence for r in rows) / total, 4) if total else None,
        "low_confidence_count": sum(1 for r in rows if r.low_confidence),
        "synthetic_count": sum(1 for r in rows if r.is_synthetic),
        "recent": [serialize_analysis(r) for r in reversed(rows[-6:])],
        "distribution": {"labels": [rules[k]["display"] for k in counts], "values": list(counts.values())},
        "monthly": {"labels": sorted(months), "values": [months[m] for m in sorted(months)]},
    }


def charts(db: Session, user_id: int) -> dict:
    rows = _rows(db, user_id)
    rules = load_rules()
    counts = Counter(r.predicted_fabric for r in rows)
    temps = Counter(r.washing_temperature for r in rows)
    days = Counter(r.created_at.date() for r in rows)
    today = utcnow().date()
    last30 = [today - timedelta(days=i) for i in range(29, -1, -1)]
    conf = Counter()
    for r in rows:
        pct = r.confidence * 100
        for lo, hi in CONF_BUCKETS:
            if lo <= pct < hi:
                conf[f"{lo}-{min(hi, 100)}%"] += 1
                break
    labels = [f"{lo}-{min(hi, 100)}%" for lo, hi in CONF_BUCKETS]
    return {
        "total": len(rows),
        "distribution": {"labels": [rules[k]["display"] for k in counts], "values": list(counts.values())},
        "temperature": {"labels": list(temps.keys()), "values": list(temps.values())},
        "frequency": {"labels": [d.isoformat() for d in last30], "values": [days.get(d, 0) for d in last30]},
        "confidence": {"labels": labels, "values": [conf.get(l, 0) for l in labels]},
        "most_common": [{"fabric": rules[k]["display"], "count": v} for k, v in counts.most_common(5)],
    }
