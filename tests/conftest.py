import io
import os
import tempfile
import uuid

# Isolated environment BEFORE the app is imported.
_TMP = tempfile.mkdtemp(prefix="fsl_test_")
from cryptography.fernet import Fernet  # noqa: E402

os.environ.update({
    "DATABASE_URL": f"sqlite:///{_TMP}/test.db",
    "UPLOAD_DIR": f"{_TMP}/uploads",
    "PROCESSED_DIR": f"{_TMP}/processed",
    "SECRET_KEY": "test-only-secret-key-not-for-production-use",
    "FERNET_KEY": Fernet.generate_key().decode(),
    "ENVIRONMENT": "test",
    "RATE_LIMIT_ENABLED": "true",
})

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.ratelimit import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.services.ml.synthetic import generate_image  # noqa: E402
from app.services.recommendation import sync_knowledge  # noqa: E402

PASSWORD = "Passw0rd123"


@pytest.fixture(scope="session", autouse=True)
def _setup():
    init_db()
    with SessionLocal() as db:
        sync_knowledge(db)
    if not (settings.model_dir / "fabric_model.joblib").exists():
        from app.services.ml.training import synthetic_training_set, train_model
        imgs, labels = synthetic_training_set(40)
        train_model(imgs, labels, settings.model_dir, "synthetic")
    yield


@pytest.fixture(autouse=True)
def _reset_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


def new_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def client():
    return new_client()


def hdr(c: TestClient) -> dict:
    """CSRF header for the client's current session."""
    return {"X-CSRF-Token": c.get("/api/auth/csrf").json()["csrf_token"]}


def register(c: TestClient, email: str | None = None, name: str = "Test User", password: str = PASSWORD):
    email = email or f"user{uuid.uuid4().hex[:8]}@test.local"
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": password}, headers=hdr(c))
    assert r.status_code == 201, r.text
    return email, password


@pytest.fixture
def user_client():
    c = new_client()
    c.email, c.password = register(c)
    return c


@pytest.fixture
def two_users():
    a, b = new_client(), new_client()
    register(a); register(b)
    return a, b


def image_bytes(fabric: str = "cotton", fmt: str = "JPEG", seed: int = 1, size: int = 160) -> bytes:
    img = generate_image(fabric, np.random.default_rng(seed), size)
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def upload(c: TestClient, data: bytes, filename: str = "fabric.jpg", ctype: str = "image/jpeg", **form):
    return c.post("/api/fabric/analyze", files={"file": (filename, data, ctype)}, data=form, headers=hdr(c))
