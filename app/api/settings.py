from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.core.config import settings as app_settings
from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.core.security import hash_password, password_policy_error, verify_password
from app.models import FabricAnalysis, User
from app.schemas import PasswordChangeIn, PreferencesIn, ProfileIn

router = APIRouter(prefix="/api/settings", tags=["Settings"], dependencies=[Depends(csrf_protect)])

FEATURES = [
    {"name": "Profile name", "status": "implemented"},
    {"name": "Password change (Argon2)", "status": "implemented"},
    {"name": "Theme preference (light / dark / system)", "status": "implemented"},
    {"name": "Notification preference (stored)", "status": "implemented"},
    {"name": "Delete my analyses and images", "status": "implemented"},
    {"name": "Email / push notifications actually sent", "status": "future"},
    {"name": "Data export (CSV/PDF)", "status": "future"},
]


@router.get("")
def get_settings(user: User = Depends(get_current_user)):
    return {"name": user.name, "email": user.email, "theme": user.theme,
            "notifications_enabled": user.notifications_enabled, "is_demo": user.is_demo,
            "created_at": user.created_at.isoformat() + "Z", "features": FEATURES}


@router.put("/profile")
def update_profile(body: ProfileIn, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.name = body.name.strip()
    db.commit()
    log_event(db, request, user.id, "settings_change", detail="profile name")
    return {"name": user.name}


@router.post("/password")
def change_password(body: PasswordChangeIn, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if not verify_password(user.password_hash, body.current_password):
        log_event(db, request, user.id, "password_change", "failed")
        raise HTTPException(400, "Current password is incorrect.")
    err = password_policy_error(body.new_password)
    if err:
        raise HTTPException(400, err)
    user.password_hash = hash_password(body.new_password)
    db.commit()
    log_event(db, request, user.id, "password_change")
    return {"ok": True}


@router.put("/preferences")
def update_preferences(body: PreferencesIn, request: Request, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    user.theme, user.notifications_enabled = body.theme, body.notifications_enabled
    db.commit()
    log_event(db, request, user.id, "settings_change", detail="preferences")
    return {"theme": user.theme, "notifications_enabled": user.notifications_enabled}


@router.delete("/data")
def delete_my_data(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = Path(app_settings.upload_dir).resolve()
    rows = db.query(FabricAnalysis).filter_by(user_id=user.id).all()
    for a in rows:
        p = (base / a.image_path).resolve()
        if not a.image_path.startswith("synthetic://") and base in p.parents and p.is_file():
            p.unlink()
        db.delete(a)
    db.commit()
    log_event(db, request, user.id, "data_deletion", detail=f"{len(rows)} analyses")
    return {"deleted": len(rows)}
