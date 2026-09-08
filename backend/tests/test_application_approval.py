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


@pytest_asyncio.fixture
async def seed_app_for_approval(db_session: AsyncSession):
    user_id = "user_appr_01"
    pref = UserPreference(
        user_id=user_id,
        target_roles=["Senior Backend Engineer"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=130000.0,
        additional_preferences={"work_authorization": "Authorized", "sponsorship_required": False},
    )
    db_session.add(pref)

    resume = Resume(
        id="res_appr_01",
        user_id=user_id,
        name="candidate_resume.pdf",
        file_reference="user_appr_01/resumes/cand.pdf",
        content_hash="hash_appr_01",
        is_default=True,
        parsed_profile={
            "name": "Jane Candidate",
            "email": "jane.cand@example.com",
            "phone": "+1-555-888-9999",
            "skills": ["Python", "FastAPI", "SQLAlchemy"],
            "experience": [{"company": "Tech Inc", "role": "Senior Dev"}],
            "links": {"linkedin": "https://linkedin.com/in/janecand"},
        },
    )
    db_session.add(resume)

    job = JobPosting(
        id="job_appr_01",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_appr_101",
        title="Senior Python Backend Developer",
        company="Acme Corp",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="High scale backend distributed systems.",
        skills=["Python", "FastAPI"],
        apply_url="https://boards.greenhouse.io/acme/jobs/101",
        source_hash="sha_appr_101",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    service = ApplicationDraftService()
    draft = await service.create_draft(
        db=db_session,
        user_id=user_id,
        job_id="job_appr_01",
        include_cover_letter=True,
    )
    return user_id, draft.id


@pytest.mark.asyncio
async def test_successful_application_approval(db_session: AsyncSession, seed_app_for_approval):
    user_id, application_id = seed_app_for_approval

    # Candidate explicitly confirms and approves
    resp = await ApprovalService.record_approval(
        db=db_session,
        user_id=user_id,
        application_id=application_id,
        confirmation_checked=True,
        user_notes="Looks great, ready to send!",
    )

    assert resp.application_id == application_id
    assert resp.status == ApplicationStatus.APPROVED.value
    assert resp.approved is True
    assert resp.ready_for_submission is True
    assert resp.approval_token.startswith("appr_")
    assert len(resp.approved_version_hash) == 64

    # Verify DB state
    approval = await ApprovalService.get_active_approval(db_session, user_id, application_id)
    assert approval is not None
    assert approval.approval_token == resp.approval_token
    assert approval.is_approved is True
    assert approval.is_revoked is False


@pytest.mark.asyncio
async def test_approval_fails_without_confirmation_checkbox(db_session: AsyncSession, seed_app_for_approval):
    user_id, application_id = seed_app_for_approval

    with pytest.raises(ValueError) as exc_info:
        await ApprovalService.record_approval(
            db=db_session,
            user_id=user_id,
            application_id=application_id,
            confirmation_checked=False,
        )
    assert "checkbox must be checked" in str(exc_info.value)


@pytest.mark.asyncio
async def test_approval_fails_with_missing_required_field(db_session: AsyncSession, seed_app_for_approval):
    user_id, application_id = seed_app_for_approval

    # Corrupt draft by removing email value
    app = await db_session.get(Application, application_id)
    pkg = dict(app.review_package)
    for field in pkg["fields"]:
        if field["field_id"] == "email":
            field["value"] = ""
    app.review_package = pkg
    await db_session.commit()

    with pytest.raises(ValueError) as exc_info:
        await ApprovalService.record_approval(
            db=db_session,
            user_id=user_id,
            application_id=application_id,
            confirmation_checked=True,
        )
    assert "Pre-submission validation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_approval_fails_with_unresolved_sensitive_question(db_session: AsyncSession, seed_app_for_approval):
    user_id, application_id = seed_app_for_approval

    # Add unresolved sensitive question requiring user input
    app = await db_session.get(Application, application_id)
    pkg = dict(app.review_package)
    pkg["custom_questions"] = [
        {
            "question_id": "q_clearance",
            "question": "Do you hold an active Top Secret security clearance?",
            "answer": None,
            "requires_user_input": True,
            "required": True,
        }
    ]
    app.review_package = pkg
    await db_session.commit()

    with pytest.raises(ValueError) as exc_info:
        await ApprovalService.record_approval(
            db=db_session,
            user_id=user_id,
            application_id=application_id,
            confirmation_checked=True,
        )
    assert "unresolved questions" in str(exc_info.value).lower() or "requires answer" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_approval_revocation(db_session: AsyncSession, seed_app_for_approval):
    user_id, application_id = seed_app_for_approval

    # First approve
    await ApprovalService.record_approval(
        db=db_session,
        user_id=user_id,
        application_id=application_id,
        confirmation_checked=True,
    )

    app = await db_session.get(Application, application_id)
    assert app.status == ApplicationStatus.APPROVED.value

    # Revoke approval
    revoked = await ApprovalService.revoke_approval(
        db=db_session,
        user_id=user_id,
        application_id=application_id,
        reason="Need to change phone number",
    )
    assert revoked is True

    # Check status reverted to PENDING_REVIEW
    await db_session.refresh(app)
    assert app.status == ApplicationStatus.PENDING_REVIEW.value

    # Active approval should now be None
    active = await ApprovalService.get_active_approval(db_session, user_id, application_id)
    assert active is None


@pytest.mark.asyncio
async def test_approval_tenant_isolation(db_session: AsyncSession, seed_app_for_approval):
    _, application_id = seed_app_for_approval
    attacker_id = "user_attacker_99"

    with pytest.raises(ValueError) as exc_info:
        await ApprovalService.record_approval(
            db=db_session,
            user_id=attacker_id,
            application_id=application_id,
            confirmation_checked=True,
        )
    assert "unauthorized" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
