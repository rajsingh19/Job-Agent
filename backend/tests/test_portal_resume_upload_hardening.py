import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from app.config import get_settings
from app.models.resume import Resume
from app.services.browser.exceptions import ResumeUploadError
from app.services.browser.resume_uploader import ResumeUploader


@pytest.mark.asyncio
async def test_resume_upload_file_extension_validation():
    settings = get_settings()
    mock_db = AsyncMock()

    # Create dummy file with forbidden extension
    invalid_file = settings.resumes_dir / "bad_script.py"
    invalid_file.write_text("print('hello')")

    mock_resume = Resume(
        id="res_test_invalid_ext",
        user_id="user_123",
        name="bad_script.py",
        file_reference=str(invalid_file),
        content_hash="hash_invalid",
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_resume
    mock_db.execute.return_value = mock_res

    page = MagicMock()
    with pytest.raises(ResumeUploadError) as excinfo:
        await ResumeUploader.upload_resume(
            page=page,
            db=mock_db,
            user_id="user_123",
            resume_id="res_test_invalid_ext",
            selector="input[type=file]",
        )
    assert "unsupported" in str(excinfo.value).lower()
    invalid_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_resume_upload_cross_tenant_isolation():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_res

    page = MagicMock()
    with pytest.raises(ResumeUploadError) as excinfo:
        await ResumeUploader.upload_resume(
            page=page,
            db=mock_db,
            user_id="user_123",
            resume_id="res_owned_by_user_456",
            selector="input[type=file]",
        )
    assert "not found or unauthorized" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_resume_upload_oversized_file_rejected():
    settings = get_settings()
    mock_db = AsyncMock()

    oversized_file = settings.resumes_dir / "large_resume.pdf"
    # Write empty file and mock stat
    oversized_file.write_bytes(b"dummy")

    mock_resume = Resume(
        id="res_large",
        user_id="user_123",
        name="large_resume.pdf",
        file_reference=str(oversized_file),
        content_hash="hash_large",
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_resume
    mock_db.execute.return_value = mock_res

    page = MagicMock()
    # Patch stat to return > 10MB
    import stat
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Path, "stat", lambda self, *args, **kwargs: MagicMock(st_size=15 * 1024 * 1024, st_mode=stat.S_IFREG | 0o644))
        with pytest.raises(ResumeUploadError) as excinfo:
            await ResumeUploader.upload_resume(
                page=page,
                db=mock_db,
                user_id="user_123",
                resume_id="res_large",
                selector="input[type=file]",
            )
        assert "exceeds size limit" in str(excinfo.value).lower()

    oversized_file.unlink(missing_ok=True)
