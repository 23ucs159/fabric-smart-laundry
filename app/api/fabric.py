import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.core.ratelimit import rate_limit
from app.core.security import decrypt_text, encrypt_text
from app.models import FabricAnalysis, User
from app.services.analytics import serialize_analysis
from app.services.ml.classifier import ModelNotAvailableError, get_classifier
from app.services.ml.validation import ImageValidationError, validate_image_bytes
from app.services.recommendation import recommend

router = APIRouter(prefix="/api/fabric", tags=["Fabric recognition"], dependencies=[Depends(csrf_protect)])


def get_owned(db: Session, user: User, analysis_id: int) -> FabricAnalysis:
    """Authorization: a record that belongs to another user is indistinguishable from a missing one."""
    a = db.query(FabricAnalysis).filter_by(id=analysis_id, user_id=user.id).first()
    if not a:
        raise HTTPException(404, "Analysis not found.")
    return a


def full_view(a: FabricAnalysis) -> dict:
    out = serialize_analysis(a)
    probs = json.loads(a.probabilities) if a.probabilities else {}
    rules_view = recommend(a.predicted_fabric, a.confidence)
    out.update({"probabilities": probs, "note": decrypt_text(a.note_encrypted), "recommendation": rules_view})
    return out


@router.post("/analyze", status_code=201, dependencies=[Depends(rate_limit("upload", "upload_limit"))])
async def analyze(request: Request, file: UploadFile = File(...), note: str = Form("", max_length=300),
                  has_dryer: bool | None = Form(None), prefer_gentle: bool = Form(False),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    try:
        img = validate_image_bytes(data, file.filename)
    except ImageValidationError as e:
        log_event(db, request, user.id, "image_upload", "failed", str(e))
        raise HTTPException(400, str(e))
    log_event(db, request, user.id, "image_upload")

    try:
        pred = get_classifier().predict(img)
    except ModelNotAvailableError as e:
        raise HTTPException(503, str(e))

    prefs = {"has_dryer": has_dryer, "prefer_gentle": prefer_gentle or None}
    rec = recommend(pred["label"], pred["confidence"], prefs)

    # Never use the client filename: store a re-encoded copy under a random name inside the user's folder.
    rel = f"{user.id}/{uuid.uuid4().hex}.jpg"
    dest = Path(settings.upload_dir) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    safe = img.convert("RGB")
    safe.thumbnail((1600, 1600))
    safe.save(dest, "JPEG", quality=90)

    a = FabricAnalysis(
        user_id=user.id, image_path=rel, predicted_fabric=pred["label"], confidence=pred["confidence"],
        washing_temperature=rec["temperature"], washing_mode=f"{rec['wash_mode']} – {rec['washing_method']}",
        drying_method=rec["drying_method"], ironing_temperature=rec["ironing_temperature"],
        special_care=rec["special_care"], low_confidence=rec["low_confidence"],
        probabilities=json.dumps(dict(list(pred["probabilities"].items())[:5])),
        note_encrypted=encrypt_text(note.strip()) if note.strip() else None, model_version=pred["model_version"])
    db.add(a)
    db.commit()
    log_event(db, request, user.id, "prediction", detail=f"analysis={a.id}")
    out = full_view(a)
    out["recommendation"] = rec  # includes the user's preferences
    return out


@router.get("/{analysis_id}")
def get_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return full_view(get_owned(db, user, analysis_id))


@router.get("/{analysis_id}/image")
def get_image(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = get_owned(db, user, analysis_id)
    base = Path(settings.upload_dir).resolve()
    path = (base / a.image_path).resolve()
    if a.image_path.startswith("synthetic://") or base not in path.parents or not path.is_file():
        raise HTTPException(404, "Image not available.")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})


@router.delete("/{analysis_id}")
def delete_analysis(analysis_id: int, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    a = get_owned(db, user, analysis_id)
    base = Path(settings.upload_dir).resolve()
    path = (base / a.image_path).resolve()
    if not a.image_path.startswith("synthetic://") and base in path.parents and path.is_file():
        path.unlink()
    db.delete(a)
    db.commit()
    log_event(db, request, user.id, "data_deletion", detail=f"analysis={analysis_id}")
    return {"ok": True}
