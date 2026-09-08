import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.services.applications.draft_service import ApplicationDraftService
from app.services.submission.approval_service import ApprovalService
from app.services.submission.audit_service import AuditService
from app.services.submission.exceptions import ApprovalRequiredError
from app.services.submission.submission_guard import SubmissionGuard


@pytest_asyncio.fixture
async def seed_tenant_apps(db_session: AsyncSession):
    user_a = "user_alice_sec"
    user_b = "user_mallory_sec"

    pref_a = UserPreference(user_id=user_a, target_roles=["Dev"], preferred_locations=["Remote"], remote_preference=RemoteType.REMOTE.value)
    pref_b = UserPreference(user_id=user_b, target_roles=["Dev"], preferred_locations=["Remote"], remote_preference=RemoteType.REMOTE.value)
    db_session.add_all([pref_a, pref_b])

    resume_a = Resume(
        id="res_alice_sec",
        user_id=user_a,
        name="alice.pdf",
        file_reference="user_alice_sec/alice.pdf",
        content_hash="hash_alice",
        parsed_profile={"name": "Alice", "email": "alice@sec.com", "phone": "+1-555-111-2222", "skills": ["Python"]},
    )
    db_session.add(resume_a)

    job = JobPosting(
        id="job_sec_01",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_sec_1",
        title="Security Engineer",
        company="VaultCorp",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="AppSec and AuthZ.",
        skills=["Python"],
        apply_url="https://boards.greenhouse.io/vault/1",
        source_hash="sha_vault_1",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    service = ApplicationDraftService()
    draft_a = await service.create_draft(db=db_session, user_id=user_a, job_id="job_sec_01", include_cover_letter=True)
    return user_a, user_b, draft_a.id


@pytest.mark.asyncio
async def test_cross_tenant_approval_rejected(db_session: AsyncSession, seed_tenant_apps):
    user_a, user_b, app_a_id = seed_tenant_apps

    # Mallory (user_b) attempts to approve Alice's application
    with pytest.raises(ValueError) as exc:
        await ApprovalService.record_approval(
            db=db_session,
            user_id=user_b,
            application_id=app_a_id,
            confirmation_checked=True,
        )
    assert "not found" in str(exc.value).lower() or "unauthorized" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_cross_tenant_submission_rejected(db_session: AsyncSession, seed_tenant_apps):
    user_a, user_b, app_a_id = seed_tenant_apps

    # Alice legitimately approves
    await ApprovalService.record_approval(
        db=db_session,
        user_id=user_a,
        application_id=app_a_id,
        confirmation_checked=True,
    )

    # Mallory attempts to trigger submission of Alice's application
    with pytest.raises(ApprovalRequiredError):
        await SubmissionGuard.authorize_submission(
            db=db_session,
            user_id=user_b,
            application_id=app_a_id,
        )


@pytest.mark.asyncio
async def test_cross_tenant_audit_trail_isolation(db_session: AsyncSession, seed_tenant_apps):
    user_a, user_b, app_a_id = seed_tenant_apps

    await ApprovalService.record_approval(
        db=db_session,
        user_id=user_a,
        application_id=app_a_id,
        confirmation_checked=True,
    )

    # Alice should see audit events
    alice_events = await AuditService.get_audit_trail(db_session, app_a_id, user_a)
    assert len(alice_events) >= 1

    # Mallory should see empty audit trail for Alice's app
    mallory_events = await AuditService.get_audit_trail(db_session, app_a_id, user_b)
    assert len(mallory_events) == 0


@pytest.mark.asyncio
async def test_audit_service_redacts_sensitive_keys(db_session: AsyncSession):
    event = await AuditService.log_event(
        db=db_session,
        application_id="app_redact_test",
        user_id="user_redact_test",
        event_type="AUTH_LOG",
        details={
            "candidate_name": "Alice",
            "session_token": "secret_session_token_xyz",
            "user_password": "super_secret_password",
            "auth_cookie": "secret_cookie_val",
        },
    )

    assert event.details["candidate_name"] == "Alice"
    assert event.details["session_token"] == "[REDACTED]"
    assert event.details["user_password"] == "[REDACTED]"
    assert event.details["auth_cookie"] == "[REDACTED]"
