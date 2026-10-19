"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.api import (analytics, assistant, auth, etl, fabric, history, ml, recommendations,
                     security, settings as settings_api)
from app.core.config import BASE_DIR, settings
from app.core.database import SessionLocal, init_db
from app.services.recommendation import sync_knowledge
from app.web import router as web_router

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
       "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
DOCS_CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: https://fastapi.tiangolo.com; "
            "worker-src blob:; connect-src 'self'; frame-ancestors 'none'")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        sync_knowledge(db)
        if settings.auto_seed_demo:
            from app.services.seed import seed_demo
            seed_demo(db)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/api/docs", redoc_url="/api/redoc",
              openapi_url="/api/openapi.json", lifespan=lifespan,
              description="Fabric recognition, care recommendation and smart laundry assistant (B.Tech Phase-II project).")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    response.headers["Content-Security-Policy"] = DOCS_CSP if path in ("/api/docs", "/api/redoc") else CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if path.startswith("/api/") or path == "/":
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
for r in (auth, fabric, recommendations, history, analytics, etl, ml, assistant, security, settings_api):
    app.include_router(r.router)
app.include_router(web_router)


@app.get("/api/health", tags=["System"])
def health():
    return {"status": "ok"}
