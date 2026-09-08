import logging
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.resume import Resume
from app.services.browser.exceptions import ResumeUploadError

logger = logging.getLogger(__name__)

# Max allowed resume file size: 10 MB
MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


class ResumeUploader:
    """
    Handles secure resume validation and upload via Playwright.
    Enforces multi-tenant isolation, directory containment, file size limits,
    and strict path traversal prevention. Raw filesystem paths are NEVER exposed.
    """

    @classmethod
    async def upload_resume(
        cls,
        page,
        db: AsyncSession,
        user_id: str,
        resume_id: str,
        selector: str,
        portal_id: Optional[str] = None,
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
            logger.error("Path traversal detected! Attempted path is outside authorized resumes directory.")
            raise ResumeUploadError("Invalid resume storage path detected.")

        if not resume_path.exists() or not resume_path.is_file():
            logger.error("Resume file does not exist for resume_id='%s'", resume_id)
            raise ResumeUploadError("Resume file not found.")

        # 3. Validate file extension
        suffix = resume_path.suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            logger.error("Unsupported file extension '%s' for resume_id='%s'", suffix, resume_id)
            raise ResumeUploadError(f"Unsupported resume file extension '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}")

        # 4. Validate file size limit
        file_size = resume_path.stat().st_size
        if file_size > MAX_RESUME_SIZE_BYTES:
            logger.error("Resume file size %d exceeds limit of %d bytes", file_size, MAX_RESUME_SIZE_BYTES)
            raise ResumeUploadError(f"Resume file exceeds size limit of {MAX_RESUME_SIZE_BYTES // (1024*1024)}MB.")

        # 5. Upload via Playwright
        try:
            file_input = page.locator(selector).first
            await file_input.set_input_files(str(resume_path))
            logger.info(
                "Successfully uploaded resume_id='%s' (filename='%s', size=%d bytes) to portal='%s'",
                resume_id,
                resume_path.name,
                file_size,
                portal_id or "unknown",
            )
            return True
        except Exception as e:
            logger.error("Playwright set_input_files failed on selector '%s'", selector)
            raise ResumeUploadError(f"Failed to upload resume file: {e}") from e
