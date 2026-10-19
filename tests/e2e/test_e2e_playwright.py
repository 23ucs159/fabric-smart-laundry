"""Browser end-to-end tests (Playwright).

Run:  pip install playwright && playwright install chromium
      uvicorn app.main:app --port 8000 &      # then
      E2E_BASE_URL=http://127.0.0.1:8000 pytest tests/e2e -v

Skipped automatically when Playwright or E2E_BASE_URL is not available (see docs/TEST_RESULTS.md).
"""
import io
import os
import uuid

import pytest

pw = pytest.importorskip("playwright.sync_api")
BASE = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="E2E_BASE_URL not set")


@pytest.fixture(scope="module")
def page():
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        yield pg
        b.close()


def test_full_user_journey(page, tmp_path):
    from PIL import Image
    import numpy as np
    from app.services.ml.synthetic import generate_image
    img = tmp_path / "fabric.jpg"
    generate_image("cotton", np.random.default_rng(1)).save(img)
    email = f"e2e{uuid.uuid4().hex[:6]}@test.local"

    page.goto(BASE + "/")
    assert "Fabric Recognition" in page.title() or page.locator("h1").first.inner_text()
    page.click("text=Create account")
    page.fill("#name", "E2E User"); page.fill("#email", email)
    page.fill("#password", "Passw0rd123"); page.fill("#confirm", "Passw0rd123")
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard")
    assert page.locator("#stat-total").inner_text() == "0"

    page.goto(BASE + "/recognize")
    page.set_input_files("#file-input", str(img))
    page.click("#analyze-btn")
    page.wait_for_selector("#result .result-head")
    page.click("text=Open full result page")
    page.wait_for_selector("#image-box img")

    page.goto(BASE + "/history")
    page.wait_for_selector("#history-body tr")
    page.goto(BASE + "/assistant")
    page.fill("#chat-input", "How should I wash wool?")
    page.press("#chat-input", "Enter")
    page.wait_for_selector(".msg.bot >> nth=1")
    page.goto(BASE + "/settings")
    page.click("#logout-btn")
    page.wait_for_url(BASE + "/")
