"""Application settings. Every secret is read from environment variables (or .env)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI-Based Fabric Recognition and Smart Laundry System"
    environment: str = "development"  # development | production | test

    # Secrets: never hard-coded. In development they are auto-generated into data/.dev_* (git-ignored).
    secret_key: str = ""
    fernet_key: str = ""

    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"

    # Session / cookies
    cookie_secure: bool = False  # set True behind HTTPS in production
    session_max_age: int = 8 * 3600

    # Recommendation thresholds (configurable)
    confidence_threshold: float = 0.60  # below this -> "verify the label" warning
    high_confidence: float = 0.80

    # Upload validation
    max_upload_mb: int = 5
    min_image_px: int = 32
    max_image_px: int = 8000

    # Rate limiting (requests per window per client)
    rate_limit_enabled: bool = True
    rate_window_seconds: int = 60
    login_limit: int = 10
    register_limit: int = 5
    upload_limit: int = 20
    assistant_limit: int = 30

    # Paths
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    knowledge_dir: Path = BASE_DIR / "data" / "knowledge"
    raw_dir: Path = BASE_DIR / "data" / "raw"
    processed_dir: Path = BASE_DIR / "data" / "processed"
    model_dir: Path = BASE_DIR / "ml" / "artifacts"

    # Optional external LLM used ONLY to rephrase retrieved text (no DB / tool access)
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"

    # Demo data
    auto_seed_demo: bool = False
    demo_password: str = "DemoPass2026"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
