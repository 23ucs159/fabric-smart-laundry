"""Password hashing (Argon2), signed session cookies, Fernet field encryption."""
import re
import secrets
from functools import lru_cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.core.config import BASE_DIR, settings

SESSION_COOKIE = "fsl_session"
_ph = PasswordHasher()
DUMMY_HASH = _ph.hash("timing-equalisation-dummy-password")


# ---------------------------------------------------------------- secrets
def _dev_secret(name: str, generator) -> str:
    """Development-only: persist an auto-generated secret outside version control."""
    if settings.environment == "production":
        raise RuntimeError(f"{name.upper()} must be set via environment variable in production")
    path = Path(BASE_DIR / "data" / f".dev_{name}")
    if path.exists():
        return path.read_text().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    value = generator()
    path.write_text(value)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return value


@lru_cache
def get_secret_key() -> str:
    return settings.secret_key or _dev_secret("secret_key", lambda: secrets.token_urlsafe(48))


@lru_cache
def _fernet() -> Fernet:
    key = settings.fernet_key or _dev_secret("fernet_key", lambda: Fernet.generate_key().decode())
    return Fernet(key.encode() if isinstance(key, str) else key)


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_policy_error(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if len(password) > 128:
        return "Password must be at most 128 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one digit."
    return None


# ---------------------------------------------------------------- sessions
def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_secret_key(), salt="fsl-session-v1")


def new_session(uid: int | None = None) -> dict:
    return {"uid": uid, "csrf": secrets.token_urlsafe(32)}


def encode_session(data: dict) -> str:
    return _serializer().dumps(data)


def decode_session(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=settings.session_max_age)
    except BadSignature:
        return None
    return data if isinstance(data, dict) and "csrf" in data else None


def set_session_cookie(response, data: dict) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        encode_session(data),
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


# ---------------------------------------------------------------- field encryption (Fernet)
def encrypt_text(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt_text(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None
