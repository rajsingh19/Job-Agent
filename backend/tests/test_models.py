import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import ApplicationStatus, ConnectorType, RemoteType, ATSProvider, ExperienceLevel
from app.models.user import User
from app.models.resume import Resume
from app.models.profile import UserPreference
from app.models.job import JobPosting
from app.models.application import Application
from app.models.status_history import ApplicationStatusHistory


@pytest.mark.asyncio
async def test_user_creation_and_relations(db_session: AsyncSession):
    user = User(email="test.candidate@example.com")
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.email == "test.candidate@example.com"
    assert user.created_at is not None

    # Add User Preference
    preference = UserPreference(
        user_id=user.id,
        target_roles=["Software Engineer", "Full Stack Developer"],
        preferred_locations=["San Francisco, CA", "Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=100000.0,
        experience_level=ExperienceLevel.ENTRY_LEVEL.value,
        required_skills=["Python", "FastAPI", "TypeScript"],
    )
    db_session.add(preference)
    await db_session.flush()

    # Add Resume
    resume = Resume(
        user_id=user.id,
        name="Software_Engineer_2026.pdf",
        file_reference="storage/resumes/Software_Engineer_2026.pdf",
        content_hash="abc123hash456",
        parsed_profile={
            "name": "Jane Doe",
            "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
            "education": [{"institution": "MIT", "degree": "B.S. CS"}],
        },
        is_default=True,
    )
    db_session.add(resume)
    await db_session.flush()

    # Add Job Posting
    job = JobPosting(
        source="GREENHOUSE",
        external_id="gh_12345",
        title="Junior Backend Engineer",
        company="TechCorp Inc.",
        location="San Francisco, CA",
        remote_type=RemoteType.HYBRID.value,
        description="We are seeking a backend engineer proficient in Python and FastAPI.",
        skills=["Python", "FastAPI", "SQLAlchemy"],
        stipend_min=90000.0,
        stipend_max=120000.0,
        apply_url="https://boards.greenhouse.io/techcorp/jobs/12345",
        ats_provider=ATSProvider.GREENHOUSE.value,
        source_hash="sha256_techcorp_12345",
    )
    db_session.add(job)
    await db_session.flush()

    # Add Application
    application = Application(
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        connector=ConnectorType.GREENHOUSE_API.value,
        status=ApplicationStatus.DISCOVERED.value,
        match_score=0.92,
        review_package={
            "job_title": "Junior Backend Engineer",
            "company": "TechCorp Inc.",
            "populated_fields": {"name": "Jane Doe", "email": "test.candidate@example.com"},
        },
    )
    db_session.add(application)
    await db_session.flush()

    # Add Status History
    history = ApplicationStatusHistory(
        application_id=application.id,
        from_status=None,
        to_status=ApplicationStatus.DISCOVERED.value,
        actor="AGENT",
        reason="Job discovered and matched with candidate profile",
    )
    db_session.add(history)
    await db_session.commit()

    # Query back and verify
    stmt = select(User).where(User.id == user.id)
    result = await db_session.execute(stmt)
    saved_user = result.scalar_one()

    assert saved_user.email == "test.candidate@example.com"
    assert len(saved_user.resumes) == 1
    assert saved_user.preference.remote_preference == RemoteType.REMOTE.value
    assert len(saved_user.applications) == 1
    assert saved_user.applications[0].job.company == "TechCorp Inc."
    assert len(saved_user.applications[0].status_history) == 1


@pytest.mark.asyncio
async def test_user_email_uniqueness(db_session: AsyncSession):
    user1 = User(email="duplicate@example.com")
    db_session.add(user1)
    await db_session.flush()

    user2 = User(email="duplicate@example.com")
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_job_posting_source_hash_uniqueness(db_session: AsyncSession):
    job1 = JobPosting(
        source="LEVER",
        title="Frontend Engineer",
        company="StartupCo",
        description="React developer",
        apply_url="https://jobs.lever.co/startup/1",
        source_hash="unique_hash_1",
    )
    db_session.add(job1)
    await db_session.flush()

    job2 = JobPosting(
        source="LEVER",
        title="Frontend Engineer Duplicate",
        company="StartupCo",
        description="React developer",
        apply_url="https://jobs.lever.co/startup/1",
        source_hash="unique_hash_1",  # Same source_hash
    )
    db_session.add(job2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_job_application_uniqueness(db_session: AsyncSession):
    user = User(email="unique.app.user@example.com")
    job = JobPosting(
        source="ASHBY",
        title="AI Engineer",
        company="AI Labs",
        description="Python LLM engineer",
        apply_url="https://jobs.ashbyhq.com/ailabs/1",
        source_hash="sha256_ailabs_1",
    )
    db_session.add_all([user, job])
    await db_session.flush()

    app1 = Application(
        user_id=user.id,
        job_id=job.id,
        status=ApplicationStatus.DISCOVERED.value,
    )
    db_session.add(app1)
    await db_session.flush()

    # Attempt second application by same user to same job
    app2 = Application(
        user_id=user.id,
        job_id=job.id,
        status=ApplicationStatus.DISCOVERED.value,
    )
    db_session.add(app2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
