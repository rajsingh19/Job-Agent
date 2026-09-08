import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.application import Application
from app.models.enums import ApplicationStatus, JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.services.applications.draft_service import ApplicationDraftService
from app.services.submission.approval_service import ApprovalService
from app.services.submission.exceptions import (
    AlreadySubmittedError,
    ApprovalExpiredError,
    ApprovalRequiredError,
    ConcurrentSubmissionError,
)
from app.services.submission.submission_guard import SubmissionGuard


@pytest_asyncio.fixture
async def seed_guard_app(db_session: AsyncSession):
    user_id = "user_guard_test"
    pref = UserPreference(
        user_id=user_id,
        target_roles=["Staff Engineer"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=160000.0,
    )
    db_session.add(pref)

    resume = Resume(
        id="res_guard_test",
        user_id=user_id,
        name="resume.pdf",
        file_reference="user_guard_test/resume.pdf",
        content_hash="hash_guard_test",
        is_default=True,
        parsed_profile={
            "name": "Guard Tester",
            "email": "guard@example.com",
            "phone": "+1-555-444-3333",
            "skills": ["Python", "FastAPI"],
        },
    )
    db_session.add(resume)

    job = JobPosting(
        id="job_guard_test",
        source="LEVER",
        source_type=JobSourceType.API.value,
        external_id="lev_guard_01",
        title="Staff Engineer",
        company="SecureCorp",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="Secure infrastructure engineering.",
        skills=["Python"],
        apply_url="https://jobs.lever.co/securecorp/1",
        source_hash="sha_guard_01",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    service = ApplicationDraftService()
    draft = await service.create_draft(
        db=db_session,
        user_id=user_id,
        job_id="job_guard_test",
        include_cover_letter=True,
    )
    return user_id, draft.id


@pytest.mark.asyncio
async def test_unapproved_submission_blocked(db_session: AsyncSession, seed_guard_app):
    user_id, app_id = seed_guard_app

    # Application is in PENDING_REVIEW, not APPROVED
    with pytest.raises(ApprovalRequiredError) as exc_info:
        await SubmissionGuard.authorize_submission(
            db=db_session,
            user_id=user_id,
            application_id=app_id,
        )
    assert "PENDING_REVIEW" in str(exc_info.value) or "Only APPROVED" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stale_approval_hash_mismatch_blocked(db_session: AsyncSession, seed_guard_app):
    user_id, app_id = seed_guard_app

    # 1. Approve valid draft
    appr_resp = await ApprovalService.record_approval(
        db=db_session,
        user_id=user_id,
        application_id=app_id,
        confirmation_checked=True,
    )

    # 2. Modify draft content behind the scenes
    app = await db_session.get(Application, app_id)
    pkg = dict(app.review_package)
    pkg["cover_letter"] = "MODIFIED cover letter after approval!"
    app.review_package = pkg
    await db_session.commit()

    # 3. Guard must detect version hash mismatch and raise ApprovalExpiredError
    with pytest.raises(ApprovalExpiredError) as exc_info:
        await SubmissionGuard.authorize_submission(
            db=db_session,
            user_id=user_id,
            application_id=app_id,
            approval_token=appr_resp.approval_token,
        )
    assert "modified after approval" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_token_mismatch_blocked(db_session: AsyncSession, seed_guard_app):
    user_id, app_id = seed_guard_app

    await ApprovalService.record_approval(
        db=db_session,
        user_id=user_id,
        application_id=app_id,
        confirmation_checked=True,
    )

    with pytest.raises(ApprovalRequiredError) as exc_info:
        await SubmissionGuard.authorize_submission(
            db=db_session,
            user_id=user_id,
            application_id=app_id,
            approval_token="forged_appr_token_999",
        )
    assert "token mismatch" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_already_submitted_application_blocked(db_session: AsyncSession, seed_guard_app):
    user_id, app_id = seed_guard_app

    app = await db_session.get(Application, app_id)
    app.status = ApplicationStatus.SUBMITTED.value
    await db_session.commit()

    with pytest.raises(AlreadySubmittedError):
        await SubmissionGuard.authorize_submission(
            db=db_session,
            user_id=user_id,
            application_id=app_id,
        )


@pytest.mark.asyncio
async def test_concurrent_submission_lock():
    app_id = "app_concurrent_test"

    async with SubmissionGuard.submission_lock(app_id):
        # Nested / parallel attempt on same application must fail immediately
        with pytest.raises(ConcurrentSubmissionError):
            async with SubmissionGuard.submission_lock(app_id):
                pass
