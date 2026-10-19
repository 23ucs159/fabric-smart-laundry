"""Smart laundry decision system: rule engine driven by data/knowledge/care_rules.json."""
import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

LOW_CONFIDENCE_MESSAGE = "Prediction confidence is low. Please verify the fabric label before washing."
CONSERVATIVE_ADVICE = "Until the fabric is verified, use cold water, a gentle cycle and no high heat."


@lru_cache
def load_rules(path: str | None = None) -> dict:
    p = Path(path) if path else settings.knowledge_dir / "care_rules.json"
    return json.loads(p.read_text(encoding="utf-8"))


def reload_rules() -> None:
    load_rules.cache_clear()


def fabric_keys() -> list[str]:
    return list(load_rules().keys())


def display_name(key: str) -> str:
    return load_rules()[key]["display"]


def confidence_level(confidence: float, threshold: float | None = None) -> str:
    threshold = settings.confidence_threshold if threshold is None else threshold
    if confidence < threshold:
        return "low"
    return "high" if confidence >= settings.high_confidence else "medium"


def recommend(fabric: str, confidence: float = 1.0, prefs: dict | None = None,
              threshold: float | None = None, rules: dict | None = None) -> dict:
    """Combine fabric class, model confidence, care knowledge and user preferences."""
    rules = rules or load_rules()
    key = (fabric or "").strip().lower()
    if key not in rules:
        raise ValueError(f"Unsupported fabric type: {fabric!r}")
    prefs = prefs or {}
    r = rules[key]
    level = confidence_level(confidence, threshold)
    low = level == "low"

    drying = r["drying_method"]
    if prefs.get("has_dryer") is True:
        drying = r["drying_with_dryer"]
    elif prefs.get("has_dryer") is False:
        drying = r["drying_without_dryer"]

    modes = r["wash_modes"]
    mode = modes[0]
    if prefs.get("prefer_gentle"):
        mode = next((m for m in ("Delicate", "Wool", "Gentle") if m in modes), modes[0])

    pct = round(confidence * 100, 1)
    explanation = (f"The system identified the material as {r['display'].lower()} with {level} confidence ({pct}%). "
                   f"{r['rationale']}")
    if low:
        explanation += " Because confidence is low, treat this as a suggestion only and check the care label."
    elif level == "medium":
        explanation += " Confidence is moderate, so please confirm against the care label."

    return {
        "fabric": key,
        "fabric_name": r["display"],
        "confidence": round(float(confidence), 4),
        "confidence_level": level,
        "low_confidence": low,
        "warning": LOW_CONFIDENCE_MESSAGE if low else None,
        "conservative_advice": CONSERVATIVE_ADVICE if low else None,
        "properties": r["properties"],
        "washing_method": r["washing_method"],
        "wash_mode": mode,
        "wash_modes": modes,
        "temperature": r["temperature"],
        "detergent": r["detergent"],
        "drying_method": drying,
        "ironing_temperature": r["ironing"],
        "bleaching": r["bleaching"],
        "special_care": r["special_care"],
        "avoid": r["avoid"],
        "explanation": explanation,
        "preferences_applied": {k: v for k, v in prefs.items() if v is not None},
    }


def sync_knowledge(db) -> int:
    """Mirror the JSON knowledge base into the relational fabric_knowledge table."""
    from app.models import FabricKnowledge

    count = 0
    for key, r in load_rules().items():
        row = db.query(FabricKnowledge).filter_by(fabric_type=key).first() or FabricKnowledge(fabric_type=key)
        row.property = ", ".join(r["properties"])
        row.washing_method = r["washing_method"]
        row.temperature = r["temperature"]
        row.drying_method = r["drying_method"]
        row.ironing_method = r["ironing"]
        row.special_care = r["special_care"]
        row.detergent = r["detergent"]
        row.bleaching = r["bleaching"]
        db.add(row)
        count += 1
    db.commit()
    return count
