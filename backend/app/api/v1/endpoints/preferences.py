from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.services.profile.service import CandidateProfileService

router = APIRouter()
profile_service = CandidateProfileService()


@router.get(
    "",
    response_model=UserPreferencesResponse,
    summary="Get user's authoritative job preferences",
)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves authoritative job preferences for the user."""
    return await profile_service.get_preferences(db=db, user_id=user_id)


@router.put(
    "",
    response_model=UserPreferencesResponse,
    summary="Update user's authoritative job preferences",
)
async def update_preferences(
    preferences_update: UserPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Updates authoritative user preferences. Resume parsing will never overwrite these."""
    return await profile_service.update_preferences(
        db=db,
        user_id=user_id,
        update_data=preferences_update,
    )
