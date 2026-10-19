import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.models import FabricAnalysis, User
from app.services.analytics import iso
from app.services.ml.classifier import model_path
from app.services.recommendation import load_rules

router = APIRouter(prefix="/api/ml", tags=["ML insights"], dependencies=[Depends(csrf_protect)])


@router.get("/info")
def info(user: User = Depends(get_current_user)):
    mp = settings.model_dir / "metrics.json"
    if not model_path().exists() or not mp.exists():
        return {"available": False, "message": "No trained model found. Run: python -m ml.train --synthetic 150"}
    m = json.loads(mp.read_text(encoding="utf-8"))
    m["available"] = True
    m["display_names"] = {k: v["display"] for k, v in load_rules().items()}
    return m


@router.get("/predictions")
def predictions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(FabricAnalysis).filter_by(user_id=user.id).order_by(FabricAnalysis.created_at.desc()).limit(15).all())
    rules = load_rules()
    return [{"id": r.id, "created_at": iso(r.created_at), "fabric": rules[r.predicted_fabric]["display"],
             "confidence": round(r.confidence, 4), "low_confidence": r.low_confidence,
             "model_version": r.model_version, "is_synthetic": r.is_synthetic} for r in rows]
