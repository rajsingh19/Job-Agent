from pathlib import Path
from app.config.settings import Settings


def test_settings_initialization(tmp_path: Path):
    temp_storage = tmp_path / "custom_storage"
    settings = Settings(
        app_name="Test Job Agent",
        app_env="testing",
        debug=False,
        database_url="sqlite+aiosqlite:///:memory:",
        storage_dir=temp_storage,
        resumes_dir=temp_storage / "resumes",
        sessions_dir=temp_storage / "sessions",
        screenshots_dir=temp_storage / "screenshots",
        require_explicit_approval=True,
    )

    assert settings.app_name == "Test Job Agent"
    assert settings.app_env == "testing"
    assert settings.require_explicit_approval is True
    assert settings.llm_provider == "mock"

    settings.ensure_directories_exist()
    assert temp_storage.exists()
    assert (temp_storage / "resumes").exists()
    assert (temp_storage / "sessions").exists()
    assert (temp_storage / "screenshots").exists()
