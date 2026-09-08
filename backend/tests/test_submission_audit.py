import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.services.applications.draft_service import ApplicationDraftService
from app.services.browser.browser_manager import BrowserManager
from app.services.submission.approval_service import ApprovalService
from app.services.submission.audit_service import AuditService
from app.services.submission.submission_service import SubmissionService


@pytest_asyncio.fixture
async def seed_audit_app(db_session: AsyncSession):
    user_id = "user_audit_test"
    pref = UserPreference(user_id=user_id, target_roles=["Engineer"], preferred_locations=["Remote"], remote_preference=RemoteType.REMOTE.value)
    db_session.add(pref)

    resume = Resume(
        id="res_audit",
        user_id=user_id,
        name="resume.pdf",
        file_reference="user_audit_test/resume.pdf",
        content_hash="hash_audit",
        parsed_profile={"name": "Audit User", "email": "audit@example.com", "phone": "+1-555-909-1234", "skills": ["Python"]},
    )
    db_session.add(resume)

    job = JobPosting(
        id="job_audit_01",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_audit_1",
        title="Audit Engineer",
        company="ComplianceCorp",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="Auditing backend.",
        skills=["Python"],
        apply_url="https://boards.greenhouse.io/comp/1",
        source_hash="sha_audit_1",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    service = ApplicationDraftService()
    draft = await service.create_draft(db=db_session, user_id=user_id, job_id="job_audit_01", include_cover_letter=True)
    return user_id, draft.id


@pytest.mark.asyncio
async def test_full_audit_trail_recorded(db_session: AsyncSession, seed_audit_app):
    user_id, app_id = seed_audit_app

    # 1. Candidate Approves
    appr = await ApprovalService.record_approval(
        db=db_session,
        user_id=user_id,
        application_id=app_id,
        confirmation_checked=True,
        user_notes="Audit test note",
    )

    # 2. Browser session with working submit button
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("sess_audit_1", user_id)
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <div id="content">
                    <button type="submit" onclick="document.getElementById('content').innerHTML='<h1>Application submitted</h1><p>Ref: AUD-100</p>'">Submit Application</button>
                </div>
            </body>
        </html>
    """)

    # 3. Submit
    await SubmissionService.execute_submission(
        db=db_session,
        user_id=user_id,
        application_id=app_id,
        approval_token=appr.approval_token,
        page=page,
    )

    # 4. Fetch audit trail
    events = await AuditService.get_audit_trail(
        db=db_session,
        application_id=app_id,
        user_id=user_id,
    )

    event_types = [e.event_type for e in events]
    assert "VALIDATION_PASSED" in event_types
    assert "APPROVED" in event_types
    assert "SUBMISSION_INITIATED" in event_types
    assert "SUBMISSION_CONFIRMED" in event_types

    # Ensure chronologically ordered
    for i in range(len(events) - 1):
        assert events[i].created_at <= events[i + 1].created_at

    await bm.close_session("sess_audit_1")
