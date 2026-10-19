from fastapi import Request
from sqlalchemy.orm import Session

from app.core.ratelimit import client_ip
from app.models import AuditLog


def log_event(db: Session, request: Request | None, user_id: int | None, action: str,
              status: str = "success", detail: str | None = None) -> None:
    """Append a security audit record. Never logs secrets or passwords."""
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        status=status,
        ip_address=client_ip(request) if request else None,
        detail=(detail or "")[:250] or None,
    ))
    db.commit()
