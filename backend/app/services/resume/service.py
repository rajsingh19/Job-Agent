import hashlib
import logging
import os
from pathlib import Path
import uuid
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import Settings, get_settings
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeProfile, ResumeResponse
from app.services.ai.provider import get_llm_provider
from app.services.exceptions import (
    FileTooLargeError,
    ForbiddenResourceAccessError,
    ResumeNotFoundError,
    UnsupportedFileTypeError,
    UserNotFoundError,
)
from app.services.resume.extractors import get_text_extractor
from app.services.resume.parser import FallbackResumeParser, LLMResumeParser

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",  # Fallback MIME for some uploaders
}


class ResumeProcessingService:
    """Coordinates resume upload, text extraction, LLM parsing, fallback, validation, and storage."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    async def _ensure_user_exists(self, db: AsyncSession, user_id: str) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            # Auto-provision user if not found in local development mode
            user = User(id=user_id, email=f"user_{user_id[:8]}@example.com")
            db.add(user)
            await db.flush()
        return user

    async def upload_resume(
        self,
        db: AsyncSession,
        user_id: str,
        original_filename: str,
        file_bytes: bytes,
        content_type: Optional[str] = None,
    ) -> Resume:
        """Validates and stores an uploaded resume securely."""
        await self._ensure_user_exists(db, user_id)

        # 1. Sanitize filename & prevent path traversal
        clean_name = Path(original_filename).name
        ext = os.path.splitext(clean_name)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"Unsupported file extension '{ext}'. Only .pdf and .docx files are permitted."
            )

        if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
            raise UnsupportedFileTypeError(
                f"Unsupported MIME type '{content_type}'. Must be PDF or DOCX."
            )

        # 2. File size validation
        file_size = len(file_bytes)
        if file_size > self.settings.max_resume_file_size_bytes:
            max_mb = self.settings.max_resume_file_size_bytes / (1024 * 1024)
            raise FileTooLargeError(max_size_mb=max_mb)

        # 3. Compute SHA-256 content hash
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        # 4. Generate safe server storage path (never expose original path or allow directory traversal)
        safe_filename = f"{uuid.uuid4()}{ext}"
        storage_path = self.settings.resumes_dir / safe_filename

        # Write to isolated storage directory
        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        # Relative reference stored in DB to avoid exposing absolute filesystem path
        file_reference = f"storage/resumes/{safe_filename}"

        # 5. Check if user already has resumes to set default
        existing_resumes_count = await db.scalar(
            select(func.count(Resume.id)).where(Resume.user_id == user_id)
        )
        is_default = (existing_resumes_count == 0)

        resume = Resume(
            user_id=user_id,
            name=clean_name,
            file_reference=file_reference,
            content_hash=content_hash,
            parsed_profile={},
            is_default=is_default,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

        return resume

    async def process_resume(
        self,
        db: AsyncSession,
        user_id: str,
        resume_id: str,
    ) -> ResumeProfile:
        """Extracts text and parses the candidate profile with LLM, falling back gracefully on failure."""
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()

        if not resume:
            raise ResumeNotFoundError(resume_id=resume_id)

        if resume.user_id != user_id:
            raise ForbiddenResourceAccessError("Cannot access resumes belonging to another user.")

        # Resolve absolute path safely from storage directory
        filename = Path(resume.file_reference).name
        full_file_path = self.settings.resumes_dir / filename

        # 1. Text Extraction
        extractor = get_text_extractor(filename)
        resume_text = await extractor.extract(full_file_path)

        # 2. Parsing (LLM with automatic fallback)
        llm_provider = get_llm_provider(self.settings)
        llm_parser = LLMResumeParser(llm_provider=llm_provider)
        fallback_parser = FallbackResumeParser()

        parsed_profile: ResumeProfile
        try:
            parsed_profile = await llm_parser.parse(resume_text)
        except Exception as e:
            logger.warning(f"LLM parsing failed for resume {resume_id}: {e}. Activating deterministic fallback parser.")
            parsed_profile = await fallback_parser.parse(resume_text)

        # 3. Persist parsed profile into database
        resume.parsed_profile = parsed_profile.model_dump()
        await db.commit()
        await db.refresh(resume)

        return parsed_profile

    async def get_resume(self, db: AsyncSession, user_id: str, resume_id: str) -> Resume:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        if not resume:
            raise ResumeNotFoundError(resume_id)
        if resume.user_id != user_id:
            raise ForbiddenResourceAccessError("Cannot access resumes belonging to another user.")
        return resume

    async def list_resumes(self, db: AsyncSession, user_id: str) -> List[Resume]:
        result = await db.execute(
            select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_resume_profile(self, db: AsyncSession, user_id: str, resume_id: str) -> ResumeProfile:
        resume = await self.get_resume(db, user_id, resume_id)
        if not resume.parsed_profile:
            # Auto-process if not yet parsed
            return await self.process_resume(db, user_id, resume_id)
        return ResumeProfile(**resume.parsed_profile)
