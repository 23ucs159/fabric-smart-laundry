from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import csrf_protect, get_current_user
from app.core.security import SESSION_COOKIE
from app.models import AuditLog, User
from app.services.analytics import iso

router = APIRouter(prefix="/api/security", tags=["Security"], dependencies=[Depends(csrf_protect)])


@router.get("/controls")
def controls(user: User = Depends(get_current_user)):
    """Describes implemented controls. Never returns secret values."""
    return {"controls": [
        {"name": "Password hashing", "status": "implemented", "detail": "Argon2id via argon2-cffi; no plain-text passwords stored."},
        {"name": "Session security", "status": "implemented",
         "detail": f"Signed, time-limited cookie '{SESSION_COOKIE}': HttpOnly, SameSite=Lax, Secure={'on' if settings.cookie_secure else 'off (enable in production)'}."},
        {"name": "CSRF protection", "status": "implemented", "detail": "Per-session token required in X-CSRF-Token for every POST/PUT/DELETE."},
        {"name": "Rate limiting", "status": "implemented",
         "detail": f"Sliding window ({settings.rate_window_seconds}s): login {settings.login_limit}, register {settings.register_limit}, upload {settings.upload_limit}, assistant {settings.assistant_limit}."},
        {"name": "Field encryption", "status": "implemented", "detail": "Fernet encryption of analysis notes; key from FERNET_KEY environment variable."},
        {"name": "Authorization", "status": "implemented", "detail": "All queries are scoped to the signed-in user; other users' records return 404."},
        {"name": "Audit logging", "status": "implemented", "detail": "Registration, login, failed login, logout, upload, prediction, deletion, settings changes."},
        {"name": "Input validation", "status": "implemented", "detail": "Pydantic schemas; image magic-byte/format/size/dimension checks; filenames never trusted."},
        {"name": "Security headers", "status": "implemented", "detail": "CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy."},
        {"name": "Assistant prompt-injection guard", "status": "implemented", "detail": "Pattern filter; assistant has no DB/tool access; optional LLM only rephrases retrieved text."},
        {"name": "Server-side session revocation", "status": "future", "detail": "Logout clears the cookie; a server-side session store is a planned enhancement."},
        {"name": "Multi-factor authentication", "status": "future", "detail": "Not implemented."},
    ]}


@router.get("/audit")
def audit(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(AuditLog).filter_by(user_id=user.id).order_by(AuditLog.id.desc()).limit(50).all()
    return [{"id": r.id, "action": r.action, "status": r.status, "ip_address": r.ip_address,
             "timestamp": iso(r.timestamp), "detail": r.detail} for r in rows]
