import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.resume import Resume
from app.models.profile import UserPreference


@pytest.mark.asyncio
async def test_database_cascade_deletion(db_session: AsyncSession):
    """Test that deleting a user cascades and removes related preferences and resumes."""
    user = User(email="cascade.test@example.com")
    db_session.add(user)
    await db_session.flush()

    pref = UserPreference(
        user_id=user.id,
        target_roles=["Data Scientist"],
    )
    db_session.add(pref)

    resume = Resume(
        user_id=user.id,
        name="resume.pdf",
        file_reference="storage/resumes/resume.pdf",
        content_hash="hash999",
        parsed_profile={"name": "Cascade User"},
    )
    db_session.add(resume)
    await db_session.commit()

    # Verify entities exist
    pref_stmt = select(UserPreference).where(UserPreference.user_id == user.id)
    pref_res = await db_session.execute(pref_stmt)
    assert pref_res.scalar_one_or_none() is not None

    resume_stmt = select(Resume).where(Resume.user_id == user.id)
    resume_res = await db_session.execute(resume_stmt)
    assert resume_res.scalar_one_or_none() is not None

    # Delete User
    await db_session.delete(user)
    await db_session.commit()

    # Verify cascaded deletion
    pref_res_after = await db_session.execute(pref_stmt)
    assert pref_res_after.scalar_one_or_none() is None

    resume_res_after = await db_session.execute(resume_stmt)
    assert resume_res_after.scalar_one_or_none() is None
