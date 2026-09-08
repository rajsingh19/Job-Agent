from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.schemas.resume import ResumeProfile, ResumeResponse
from app.services.resume.service import ResumeProcessingService

router = APIRouter()
resume_service = ResumeProcessingService()


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new resume file (PDF/DOCX)",
)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts PDF or DOCX resume, validates file type and size, generates content hash,
    and securely stores the document.
    """
    file_bytes = await file.read()
    resume = await resume_service.upload_resume(
        db=db,
        user_id=user_id,
        original_filename=file.filename or "resume.pdf",
        file_bytes=file_bytes,
        content_type=file.content_type,
    )
    return resume


@router.get(
    "",
    response_model=List[ResumeResponse],
    summary="List all uploaded resumes for the current user",
)
async def list_resumes(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns list of uploaded resumes for the authenticated user."""
    return await resume_service.list_resumes(db=db, user_id=user_id)


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Get resume metadata and parsed profile",
)
async def get_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves specific resume by ID."""
    return await resume_service.get_resume(db=db, user_id=user_id, resume_id=resume_id)


@router.post(
    "/{resume_id}/parse",
    response_model=ResumeProfile,
    summary="Extract text and parse resume into structured candidate profile",
)
async def parse_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Runs text extraction, LLM structured extraction, Pydantic validation,
    and automatic fallback if LLM is unavailable.
    """
    return await resume_service.process_resume(db=db, user_id=user_id, resume_id=resume_id)


@router.get(
    "/{resume_id}/profile",
    response_model=ResumeProfile,
    summary="Get structured profile for a specific resume",
)
async def get_resume_profile(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves or generates structured parsed profile for a resume."""
    return await resume_service.get_resume_profile(db=db, user_id=user_id, resume_id=resume_id)
