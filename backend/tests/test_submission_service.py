import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.application import Application
from app.models.enums import ApplicationStatus, JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.services.applications.draft_service import ApplicationDraftService
from app.services.browser.browser_manager import BrowserManager
from app.services.submission.approval_service import ApprovalService
from app.services.submission.models import ConfirmationStatus
from app.services.submission.submission_service import SubmissionService


@pytest_asyncio.fixture
async def seed_submission_env(db_session: AsyncSession):
    user_id = "user_sub_srv"
    pref = UserPreference(
        user_id=user_id,
        target_roles=["Lead Developer"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=140000.0,
    )
    db_session.add(pref)

    resume = Resume(
        id="res_sub_srv",
        user_id=user_id,
        name="resume.pdf",
        file_reference="user_sub_srv/resume.pdf",
        content_hash="hash_sub_srv",
        is_default=True,
        parsed_profile={
            "name": "Sarah Connor",
            "email": "sarah.connor@example.com",
            "phone": "+1-555-777-1234",
            "skills": ["Python", "FastAPI"],
        },
    )
    db_session.add(resume)

    job = JobPosting(
        id="job_sub_srv",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_srv_01",
        title="Lead Developer",
        company="Cyberdyne Systems",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="Autonomous systems backend.",
        skills=["Python"],
        apply_url="https://boards.greenhouse.io/cyberdyne/jobs/1",
        source_hash="sha_cyberdyne_1",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    service = ApplicationDraftService()
    draft = await service.create_draft(
        db=db_session,
        user_id=user_id,
        job_id="job_sub_srv",
        include_cover_letter=True,
    )
    return user_id, draft.id


@pytest.mark.asyncio
async def test_full_submission_orchestration_confirmed(db_session: AsyncSession, seed_submission_env):
    user_id, app_id = seed_submission_env

    # 1. Human candidate explicitly approves
    appr_resp = await ApprovalService.record_approval(
        db=db_session,
        user_id=user_id,
        application_id=app_id,
        confirmation_checked=True,
    )

    # 2. Browser session with working submit button
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("sess_sub_srv_1", user_id)
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <div id="wrapper">
                    <button type="submit" onclick="document.getElementById('wrapper').innerHTML='<h1>Application received</h1><p>Confirmation: REF-CYBER-101</p>'">Submit Application</button>
                </div>
            </body>
        </html>
    """)

    # 3. Execute submission
    sub_resp = await SubmissionService.execute_submission(
        db=db_session,
        user_id=user_id,
        application_id=app_id,
        approval_token=appr_resp.approval_token,
        page=page,
    )

    assert sub_resp.application_id == app_id
    assert sub_resp.status == ApplicationStatus.SUBMITTED.value
    assert sub_resp.confirmation_reference == "REF-CYBER-101"

    # Verify DB application state
    app = await db_session.get(Application, app_id)
    assert app.status == ApplicationStatus.SUBMITTED.value
    assert app.submitted_at is not None
    assert app.submission_response.get("status") == ConfirmationStatus.CONFIRMED.value

    await bm.close_session("sess_sub_srv_1")


@pytest.mark.asyncio
async def test_submission_ambiguous_transitions_to_requires_user_action(db_session: AsyncSession, seed_submission_env):
    user_id, app_id = seed_submission_env

    appr_resp = await ApprovalService.record_approval(
        db=db_session,
        user_id=user_id,
        application_id=app_id,
        confirmation_checked=True,
    )

    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("sess_sub_srv_2", user_id)
    page = sess.page

    # Page where clicking submit does not show confirmation or error
    await page.set_content("""
        <html>
            <body>
                <button type="submit" onclick="document.body.style.backgroundColor='blue'">Submit Application</button>
            </body>
        </html>
    """)

    sub_resp = await SubmissionService.execute_submission(
        db=db_session,
        user_id=user_id,
        application_id=app_id,
        approval_token=appr_resp.approval_token,
        page=page,
    )

    assert sub_resp.status == ApplicationStatus.REQUIRES_USER_ACTION.value
    assert len(sub_resp.warnings) > 0

    app = await db_session.get(Application, app_id)
    assert app.status == ApplicationStatus.REQUIRES_USER_ACTION.value

    await bm.close_session("sess_sub_srv_2")
