from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.audit import log_event
from app.core.database import get_db, utcnow
from app.core.deps import csrf_protect, get_optional_user, read_session
from app.core.ratelimit import rate_limit
from app.core.security import (DUMMY_HASH, clear_session_cookie, hash_password, new_session,
                               password_policy_error, set_session_cookie, verify_password)
from app.models import User
from app.schemas import LoginIn, RegisterIn

router = APIRouter(prefix="/api/auth", tags=["Authentication"], dependencies=[Depends(csrf_protect)])


def user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "theme": u.theme, "is_demo": u.is_demo}


@router.get("/csrf")
def csrf(request: Request):
    """Returns the CSRF token bound to the current session (creates an anonymous session if needed)."""
    sess = read_session(request)
    resp = JSONResponse({"csrf_token": (sess or {}).get("csrf")})
    if not sess:
        sess = new_session()
        resp = JSONResponse({"csrf_token": sess["csrf"]})
        set_session_cookie(resp, sess)
    return resp


@router.post("/register", status_code=201, dependencies=[Depends(rate_limit("register", "register_limit"))])
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    err = password_policy_error(body.password)
    if err:
        raise HTTPException(400, err)
    email = body.email.strip().lower()
    if db.query(User).filter_by(email=email).first():
        log_event(db, request, None, "register", "failed", "email already registered")
        raise HTTPException(409, "An account with this email already exists.")
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password), last_login=utcnow())
    db.add(user)
    db.commit()
    log_event(db, request, user.id, "register")
    sess = new_session(user.id)
    resp = JSONResponse({"user": user_out(user), "csrf_token": sess["csrf"]}, status_code=201)
    set_session_cookie(resp, sess)
    return resp


@router.post("/login", dependencies=[Depends(rate_limit("login", "login_limit"))])
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter_by(email=email).first()
    ok = verify_password(user.password_hash if user else DUMMY_HASH, body.password)
    if not user or not ok:
        log_event(db, request, user.id if user else None, "login", "failed")
        raise HTTPException(401, "Invalid email or password.")
    user.last_login = utcnow()
    db.commit()
    log_event(db, request, user.id, "login")
    sess = new_session(user.id)  # rotate session + CSRF token on login (prevents fixation)
    resp = JSONResponse({"user": user_out(user), "csrf_token": sess["csrf"]})
    set_session_cookie(resp, sess)
    return resp


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    if user:
        log_event(db, request, user.id, "logout")
    resp = JSONResponse({"ok": True})
    clear_session_cookie(resp)
    return resp


@router.get("/me")
def me(user: User | None = Depends(get_optional_user)):
    if not user:
        raise HTTPException(401, "Authentication required.")
    return user_out(user)
