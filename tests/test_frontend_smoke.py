"""Frontend smoke tests (server-rendered shells + static assets). Browser-level tests: tests/e2e/."""
import re
from pathlib import Path

import pytest

from tests.conftest import new_client, register

ROOT = Path(__file__).parents[1] / "app"
PUBLIC = ["/", "/login", "/register"]
PRIVATE = ["/dashboard", "/recognize", "/recommendation", "/history", "/analytics", "/data-engineering",
           "/ml-insights", "/assistant", "/security", "/settings"]


@pytest.mark.parametrize("path", PUBLIC)
def test_public_pages_render(client, path):
    r = client.get(path)
    assert r.status_code == 200 and 'name="csrf-token"' in r.text and "/static/css/style.css" in r.text


def test_landing_has_required_sections(client):
    t = client.get("/").text
    for s in ["AI-Based Fabric Recognition and Smart Laundry System", "How it works", "Major features",
              "About the AI and machine learning", "smart laundry idea", "Get started"]:
        assert s in t, s


@pytest.mark.parametrize("path", PRIVATE + ["/analysis/1"])
def test_private_pages_render_for_logged_in_user(user_client, path):
    r = user_client.get(path)
    assert r.status_code == 200 and "Log out" in r.text and "chart.umd.js" in r.text


def test_fourteen_pages_exist():
    assert len(PUBLIC) + len(PRIVATE) + 1 == 14


def test_logged_in_user_skips_login_page(user_client):
    assert user_client.get("/login", follow_redirects=False).headers["location"] == "/dashboard"


def test_static_assets_served(client):
    for p in ["/static/css/style.css", "/static/js/app.js", "/static/js/chart.umd.js"]:
        assert client.get(p).status_code == 200, p


def test_templates_have_no_inline_scripts_or_styles():
    for f in (ROOT / "templates").glob("*.html"):
        t = f.read_text()
        assert not re.search(r"<script(?![^>]*\bsrc=)", t), f.name
        assert " style=" not in t and "onclick=" not in t, f.name


def test_every_js_element_id_exists_in_its_template():
    """Each page handler's $('#id') lookups must exist in that page's template (catches dead buttons)."""
    js = (ROOT / "static/js/app.js").read_text()
    mapping = {"login": "login", "register": "register", "dashboard": "dashboard", "recognize": "recognize",
               "result": "result", "recommendation": "recommendation", "history": "history", "analytics": "analytics",
               "etl": "data_engineering", "ml": "ml_insights", "assistant": "assistant", "security": "security", "settings": "settings"}
    for page, tpl in mapping.items():
        m = re.search(rf"pages\.{page} = (?:async )?\(\) => \{{(.*?)\n  \}};\n", js, re.S)
        assert m, page
        ids = set(re.findall(r"\$\('#([\w-]+)'\)", m.group(1)))
        text = (ROOT / "templates" / f"{tpl}.html").read_text()
        missing = {i for i in ids if f'id="{i}"' not in text}
        # elements created by the script itself are allowed
        assert not missing - {"ml-banner"} or missing <= set(), (page, missing)


def test_forms_have_labels(client):
    t = client.get("/login").text
    assert 'for="email"' in t and 'for="password"' in t and "skip-link" in t and '<html lang="en"' in t
