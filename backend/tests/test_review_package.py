import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.services.applications.draft_service import ApplicationDraftService


@pytest.mark.asyncio
async def test_review_package_generation_and_structure(db_session: AsyncSession):
    # Seed user, preference, resume, job
    user_id = "user_rev_pkg"
    pref = UserPreference(
        user_id=user_id,
        target_roles=["Backend Engineer"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=100000.0,
    )
    db_session.add(pref)

    resume = Resume(
        id="res_rev_pkg",
        user_id=user_id,
        name="resume_pkg.pdf",
        file_reference="user_rev_pkg/resumes/resume.pdf",
        content_hash="hash_rev_pkg",
        parsed_profile={
            "name": "Package Candidate",
            "email": "package.cand@example.com",
            "phone": "+1-555-7777",
            "skills": ["Python", "FastAPI"],
        },
    )
    db_session.add(resume)

    job = JobPosting(
        id="job_rev_pkg",
        source="ASHBY",
        source_type=JobSourceType.API.value,
        external_id="ashby_pkg_1",
        title="Software Engineer - Core Platform",
        company="AshbyCorp",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="Core platform engineering with Python",
        skills=["Python"],
        apply_url="https://jobs.ashbyhq.com/ashbycorp/1",
        source_hash="sha_ashby_pkg",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    service = ApplicationDraftService()
    draft = await service.create_draft(
        db=db_session,
        user_id=user_id,
        job_id="job_rev_pkg",
        include_cover_letter=True,
    )

    review_pkg = await service.get_review_package(
        db=db_session,
        user_id=user_id,
        application_id=draft.id,
    )

    assert review_pkg.application_id == draft.id
    assert review_pkg.user_id == user_id
    assert review_pkg.job.title == "Software Engineer - Core Platform"
    assert review_pkg.job.company == "AshbyCorp"
    assert review_pkg.selected_resume is not None
    assert review_pkg.selected_resume.id == "res_rev_pkg"
    assert len(review_pkg.fields) >= 5
    assert review_pkg.cover_letter is not None
    assert isinstance(review_pkg.screenshots, list)
    assert review_pkg.ready_for_review is True
