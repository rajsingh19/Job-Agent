from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """
    Strongly-typed application settings loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application
    app_name: str = "Job Application Agent"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "dev-secret-key-job-application-agent-2026-safe-local"

    # Database
    database_url: str = "sqlite+aiosqlite:///./storage/job_agent.db"

    # Storage Paths
    storage_dir: Path = Field(default=BASE_DIR / "storage")
    resumes_dir: Path = Field(default=BASE_DIR / "storage" / "resumes")
    sessions_dir: Path = Field(default=BASE_DIR / "storage" / "sessions")
    screenshots_dir: Path = Field(default=BASE_DIR / "storage" / "screenshots")

    # AI / LLM Provider Configuration (Vendor Agnostic)
    llm_provider: str = "mock"
    llm_api_key: str = "mock-key"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2

    # Embedding Provider Configuration
    embedding_provider: str = "mock"
    embedding_api_key: str = "mock-key"
    embedding_model: str = "text-embedding-3-small"

    # Browser Automation Configuration
    browser_headless: bool = True
    browser_slow_mo_ms: int = 50
    browser_timeout_ms: int = 30000

    # Rate Limiting & Automation Safety
    max_applications_per_day: int = 20
    discovery_interval_minutes: int = 360
    enable_auto_drafting: bool = True

    # Human-In-The-Loop Enforcement
    require_explicit_approval: bool = True

    def ensure_directories_exist(self) -> None:
        """Ensures all configured storage directories exist."""
        for path in [self.storage_dir, self.resumes_dir, self.sessions_dir, self.screenshots_dir]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings dependency."""
    settings = Settings()
    settings.ensure_directories_exist()
    return settings
