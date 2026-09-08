import logging
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.resume import Resume
from app.services.browser.exceptions import ResumeUploadError

logger = logging.getLogger(__name__)


class ResumeUploader:
    """
    Handles secure resume validation and upload via Playwright.
    Enforces multi-tenant isolation, directory containment, and path traversal prevention.
    """

    @classmethod
    async def upload_resume(
        cls,
        page,
        db: AsyncSession,
        user_id: str,
        resume_id: str,
        selector: str,
    ) -> bool:
        """
        Validates the resume file for user_id and uploads it to the given file input selector.
        """
        settings = get_settings()

        # 1. Fetch Resume record and verify ownership
        stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        result = await db.execute(stmt)
        resume = result.scalars().first()

        if not resume:
            logger.error("Resume '%s' not found or does not belong to user '%s'", resume_id, user_id)
            raise ResumeUploadError(f"Resume '{resume_id}' not found or unauthorized.")

        # 2. Validate path containment and traversal
        raw_ref = getattr(resume, "file_reference", None) or getattr(resume, "file_path", None)
        if not raw_ref:
            raise ResumeUploadError("Resume record has no associated file reference.")

        res_p = Path(raw_ref)
        if not res_p.is_absolute():
            resume_path = (settings.storage_dir.parent / res_p).resolve()
        else:
            resume_path = res_p.resolve()

        resumes_dir = settings.resumes_dir.resolve()

        if not str(resume_path).startswith(str(resumes_dir)):
            logger.error("Path traversal detected! Resume path '%s' is outside '%s'", resume_path, resumes_dir)
            raise ResumeUploadError("Invalid resume storage path detected.")

        if not resume_path.exists() or not resume_path.is_file():
            logger.error("Resume file does not exist on disk: %s", resume_path)
            raise ResumeUploadError("Resume file not found on disk.")

        # 3. Validate file extension
        suffix = resume_path.suffix.lower()
        if suffix not in (".pdf", ".docx"):
            logger.error("Unsupported file extension for resume: %s", suffix)
            raise ResumeUploadError(f"Unsupported resume file extension '{suffix}'.")

        # 4. Upload via Playwright
        try:
            file_input = page.locator(selector).first
            await file_input.set_input_files(str(resume_path))
            logger.info("Successfully uploaded resume '%s' for user '%s'", resume_id, user_id)
            return True
        except Exception as e:
            logger.error("Playwright set_input_files failed on selector '%s': %s", selector, e)
            raise ResumeUploadError(f"Failed to upload resume file: {e}") from e
