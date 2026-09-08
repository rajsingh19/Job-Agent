import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.models.user import User
from app.schemas.preferences import (
    UserPreferencesCreate,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from app.schemas.resume import CandidateProfile, ResumeProfile
from app.services.exceptions import ResumeNotFoundError, UserNotFoundError

logger = logging.getLogger(__name__)


class CandidateProfileService:
    """Manages explicit user preferences and constructs candidate profiles."""

    async def _ensure_user_exists(self, db: AsyncSession, user_id: str) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(id=user_id, email=f"user_{user_id[:8]}@example.com")
            db.add(user)
            await db.flush()
        return user

    async def get_preferences(self, db: AsyncSession, user_id: str) -> UserPreference:
        """Retrieves user preferences, creating a default profile if none exists."""
        await self._ensure_user_exists(db, user_id)

        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()
        if not pref:
            pref = UserPreference(
                user_id=user_id,
                target_roles=[],
                preferred_locations=[],
                remote_preference="ANY",
                minimum_stipend=None,
                required_skills=[],
                excluded_companies=[],
                preferred_company_types=[],
                additional_preferences={},
            )
            db.add(pref)
            await db.commit()
            await db.refresh(pref)
        return pref

    async def update_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        update_data: UserPreferencesUpdate,
    ) -> UserPreference:
        """Updates authoritative user preferences."""
        pref = await self.get_preferences(db, user_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                if key == "remote_preference" and hasattr(value, "value"):
                    setattr(pref, key, value.value)
                elif key == "experience_level" and hasattr(value, "value"):
                    setattr(pref, key, value.value)
                else:
                    setattr(pref, key, value)

        await db.commit()
        await db.refresh(pref)
        return pref

    async def get_candidate_profile(
        self,
        db: AsyncSession,
        user_id: str,
        resume_id: Optional[str] = None,
    ) -> CandidateProfile:
        """
        Combines parsed ResumeProfile and authoritative UserPreferences
        without mutating or overwriting either source.
        """
        await self._ensure_user_exists(db, user_id)
        preferences_model = await self.get_preferences(db, user_id)
        preferences_response = UserPreferencesResponse.model_validate(preferences_model).model_dump()

        # Find requested or default resume
        resume: Optional[Resume] = None
        if resume_id:
            res_result = await db.execute(
                select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
            )
            resume = res_result.scalar_one_or_none()
            if not resume:
                raise ResumeNotFoundError(resume_id)
        else:
            # Look for default resume
            res_result = await db.execute(
                select(Resume)
                .where(Resume.user_id == user_id)
                .order_by(Resume.is_default.desc(), Resume.created_at.desc())
            )
            resume = res_result.scalars().first()

        resume_profile = (
            ResumeProfile(**resume.parsed_profile)
            if (resume and resume.parsed_profile)
            else ResumeProfile()
        )

        return CandidateProfile(
            user_id=user_id,
            resume_id=resume.id if resume else None,
            resume_profile=resume_profile,
            preferences=preferences_response,
        )
