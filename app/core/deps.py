import hmac

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import SESSION_COOKIE, decode_session
from app.models import User

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def read_session(request: Request) -> dict | None:
    if not hasattr(request.state, "_session"):
        request.state._session = decode_session(request.cookies.get(SESSION_COOKIE))
    return request.state._session


def csrf_protect(request: Request) -> None:
    """Reject state-changing requests that lack a valid X-CSRF-Token header."""
    if request.method in SAFE_METHODS:
        return
    sess = read_session(request)
    token = request.headers.get("x-csrf-token", "")
    if not sess or not token or not hmac.compare_digest(token, sess["csrf"]):
        raise HTTPException(403, "CSRF token missing or invalid.")


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    sess = read_session(request)
    if not sess or not sess.get("uid"):
        return None
    return db.get(User, sess["uid"])


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(401, "Authentication required.")
    return user
