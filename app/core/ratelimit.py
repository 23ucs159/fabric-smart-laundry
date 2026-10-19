"""Simple in-memory sliding-window rate limiter (single-process; use Redis/API Gateway in production)."""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.config import settings


class RateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return False, max(1, int(window - (now - q[0])))
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, setting_name: str):
    """FastAPI dependency factory: limit read from settings at request time (configurable)."""

    def dependency(request: Request):
        if not settings.rate_limit_enabled:
            return
        limit = getattr(settings, setting_name)
        ok, retry = limiter.allow(f"{scope}:{client_ip(request)}", limit, settings.rate_window_seconds)
        if not ok:
            raise HTTPException(429, "Too many requests. Please slow down.", headers={"Retry-After": str(retry)})

    return dependency
