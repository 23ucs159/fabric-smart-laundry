"""HTML page routes (server-rendered shells; data is loaded by JavaScript from the JSON API)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import BASE_DIR
from app.core.deps import get_optional_user, read_session
from app.core.security import new_session, set_session_cookie
from app.models import User

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

NAV_MAIN = [
    ("dashboard", "/dashboard", "Dashboard"), ("recognize", "/recognize", "Fabric recognition"),
    ("history", "/history", "History"), ("assistant", "/assistant", "Smart assistant"),
]
NAV_MORE = [
    ("recommendation", "/recommendation", "Washing recommendation"), ("analytics", "/analytics", "Analytics"),
    ("etl", "/data-engineering", "Data engineering"), ("ml", "/ml-insights", "ML insights"),
    ("security", "/security", "Security"), ("settings", "/settings", "Settings"),
]


def render(request: Request, name: str, page: str, user: User | None, **ctx):
    sess = read_session(request)
    fresh = None
    if not sess:
        sess = fresh = new_session()
    response = templates.TemplateResponse(request, name, {
        "page": page, "user": user, "nav_main": NAV_MAIN, "nav_more": NAV_MORE, "csrf_token": sess["csrf"],
        "theme": user.theme if user else "light", **ctx})
    if fresh:
        set_session_cookie(response, fresh)
    return response


def _private(page_name: str, template: str, path: str):
    def view(request: Request, user: User | None = Depends(get_optional_user)):
        if not user:
            return RedirectResponse(f"/login?next={path}", status_code=303)
        return render(request, template, page_name, user)
    return view


@router.get("/")
def landing(request: Request, user: User | None = Depends(get_optional_user)):
    return render(request, "landing.html", "landing", user)


@router.get("/login")
def login_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "login.html", "login", None)


@router.get("/register")
def register_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "register.html", "register", None)


for _page, _tpl, _path in [
    ("dashboard", "dashboard.html", "/dashboard"), ("recognize", "recognize.html", "/recognize"),
    ("recommendation", "recommendation.html", "/recommendation"), ("history", "history.html", "/history"),
    ("analytics", "analytics.html", "/analytics"), ("etl", "data_engineering.html", "/data-engineering"),
    ("ml", "ml_insights.html", "/ml-insights"), ("assistant", "assistant.html", "/assistant"),
    ("security", "security.html", "/security"), ("settings", "settings.html", "/settings"),
]:
    router.add_api_route(_path, _private(_page, _tpl, _path), methods=["GET"])


@router.get("/analysis/{analysis_id}")
def analysis_page(analysis_id: int, request: Request, user: User | None = Depends(get_optional_user)):
    if not user:
        return RedirectResponse(f"/login?next=/analysis/{analysis_id}", status_code=303)
    return render(request, "result.html", "result", user, analysis_id=analysis_id)
