from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.application import Application
from app.models.enums import ApplicationStatus, JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.services.applications.draft_service import ApplicationDraftService
from app.services.submission.exceptions import AlreadySubmittedError
from app.services.submission.submission_guard import SubmissionGuard
from app.services.submission.submission_service import SubmissionService


@pytest_asyncio.fixture
async def seed_submitted_app(db_session: AsyncSession):
    user_id = "user_idempotent"
    pref = UserPreference(
        user_id=user_id,
        target_roles=["Senior Engineer"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=120000.0,
    )
    db_session.add(pref)

    resume = Resume(
        id="res_idem",
        user_id=user_id,
        name="resume.pdf",
        file_reference="user_idempotent/resume.pdf",
        content_hash="hash_idem",
        is_default=True,
        parsed_profile={
            "name": "Alex Dev",
            "email": "alex@example.com",
            "phone": "+1-555-321-7654",
            "skills": ["Python"],
        },
    )
    db_session.add(resume)

    job = JobPosting(
        id="job_idem",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_idem_1",
        title="Senior Engineer",
        company="Fintech Corp",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="Core banking engine.",
        skills=["Python"],
        apply_url="https://boards.greenhouse.io/fintech/jobs/1",
        source_hash="sha_idem_1",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    service = ApplicationDraftService()
    draft = await service.create_draft(
        db=db_session,
        user_id=user_id,
        job_id="job_idem",
        include_cover_letter=True,
    )

    # Set as already SUBMITTED
    app = await db_session.get(Application, draft.id)
    app.status = ApplicationStatus.SUBMITTED.value
    app.submitted_at = datetime.now(timezone.utc)
    app.submission_response = {"status": "CONFIRMED", "confirmation_reference": "CONF-IDEM-001"}
    await db_session.commit()

    return user_id, draft.id


@pytest.mark.asyncio
async def test_guard_rejects_already_submitted_application(db_session: AsyncSession, seed_submitted_app):
    user_id, app_id = seed_submitted_app

    with pytest.raises(AlreadySubmittedError) as exc_info:
        await SubmissionGuard.authorize_submission(
            db=db_session,
            user_id=user_id,
            application_id=app_id,
        )
    assert "already been submitted" in str(exc_info.value).lower()
    assert "duplicate submission is blocked" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_service_rejects_already_submitted_application(db_session: AsyncSession, seed_submitted_app):
    user_id, app_id = seed_submitted_app

    with pytest.raises(AlreadySubmittedError) as exc_info:
        await SubmissionService.execute_submission(
            db=db_session,
            user_id=user_id,
            application_id=app_id,
        )
    assert "already been submitted" in str(exc_info.value).lower()
