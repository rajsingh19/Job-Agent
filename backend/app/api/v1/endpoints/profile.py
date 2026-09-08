from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.schemas.resume import CandidateProfile
from app.services.profile.service import CandidateProfileService

router = APIRouter()
profile_service = CandidateProfileService()


@router.get(
    "",
    response_model=CandidateProfile,
    summary="Get combined candidate profile (ResumeProfile + UserPreferences)",
)
async def get_combined_candidate_profile(
    resume_id: Optional[str] = Query(None, description="Optional specific resume ID to combine with preferences"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the unified CandidateProfile combining structured ResumeProfile and
    authoritative UserPreferences without mutating either source.
    """
    return await profile_service.get_candidate_profile(
        db=db,
        user_id=user_id,
        resume_id=resume_id,
    )
