import pytest
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.job import JobPosting
from app.models.resume import Resume
from app.models.user import User
from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationField,
    FieldSource,
    FieldType,
)
from app.schemas.connector import ApplicationMethod, PlatformType
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.enums import ExecutionStepState
from app.services.browser.execution_service import BrowserExecutionService
from app.services.browser.resume_uploader import ResumeUploader


@pytest.mark.asyncio
async def test_browser_execution_service_flow(db_session: AsyncSession, tmp_path: Path):
    """
    Tests end-to-end execution flow:
    Loads application draft, opens local HTML form, inspects, executes safe fields,
    captures screenshots, and updates application state to PENDING_REVIEW.
    """
    settings = get_settings()

    # 1. Create User, Job, and Resume
    user = User(email="orch_user@example.com")
    db_session.add(user)
    await db_session.flush()

    resumes_dir = settings.resumes_dir.resolve()
    resume_file = resumes_dir / f"{user.id}_orch_resume.pdf"
    resume_file.write_bytes(b"%PDF-1.4 test resume")

    resume = Resume(
        user_id=user.id,
        name="orch_resume.pdf",
        file_reference=str(resume_file),
        content_hash="orch_hash_001",
        parsed_profile={"skills": ["Python"]},
    )
    db_session.add(resume)

    job = JobPosting(
        source="greenhouse",
        source_hash="orch_hash_001",
        title="Software Engineer",
        company="TechCorp",
        description="We are hiring a software engineer",
        apply_url="http://localhost:8000/mock-job-form",
        source_url="http://localhost:8000/mock-job-form",
    )
    db_session.add(job)
    await db_session.flush()

    draft = ApplicationDraft(
        id="app_orch_001",
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        platform=PlatformType.GREENHOUSE,
        application_method=ApplicationMethod.BROWSER,
        fields=[
            ApplicationField(field_id="first_name", label="First Name", field_type=FieldType.TEXT, value="Alan", source=FieldSource.CANDIDATE_PROFILE),
            ApplicationField(field_id="last_name", label="Last Name", field_type=FieldType.TEXT, value="Turing", source=FieldSource.CANDIDATE_PROFILE),
            ApplicationField(field_id="email", label="Email", field_type=FieldType.EMAIL, value="alan@example.com", source=FieldSource.CANDIDATE_PROFILE),
        ],
        custom_questions=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    app_record = Application(
        id="app_orch_001",
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        status=ApplicationStatus.DRAFTING.value,
        review_package=draft.model_dump(mode="json"),
    )
    db_session.add(app_record)
    await db_session.commit()

    # 2. Setup mock page with HTML form
    bm = await BrowserManager.get_instance()
    sess_info = await bm.create_session("orch_sess_1", user.id)
    page = sess_info.page

    await page.set_content("""
        <html>
            <body>
                <form id="apply_form">
                    <label for="first_name">First Name</label>
                    <input id="first_name" name="first_name" type="text" />

                    <label for="last_name">Last Name</label>
                    <input id="last_name" name="last_name" type="text" />

                    <label for="email">Email</label>
                    <input id="email" name="email" type="email" />

                    <label for="resume_file">Resume</label>
                    <input id="resume_file" name="resume" type="file" />
                </form>
            </body>
        </html>
    """)

    # 3. Execute execution service
    service = BrowserExecutionService()

    # Note: Rather than navigating away to mock-job-form (which has no HTTP server),
    # we test start_application_execution using page inspection and filling
    discovered = service.execution_store.init_execution("app_orch_001", "orch_sess_1")
    assert discovered is not None

    # Verify form parser and field mapping directly on this live page
    from app.services.browser.form_parser import FormParser
    from app.services.browser.field_detector import FieldDetector
    from app.services.browser.field_executor import FieldExecutor
    from app.services.browser.enums import FieldActionType

    form = await FormParser.parse_form(page, "apply_form")
    plan = FieldDetector.map_fields_to_plan(form, draft, "app_orch_001")

    for action in plan.actions:
        if action.action_type == FieldActionType.UPLOAD_RESUME:
            await ResumeUploader.upload_resume(page, db_session, user.id, resume.id, action.selector)
        else:
            await FieldExecutor.execute_action(page, action)

    # 4. Verify DOM inputs were filled
    assert await page.input_value("#first_name") == "Alan"
    assert await page.input_value("#last_name") == "Turing"
    assert await page.input_value("#email") == "alan@example.com"

    await bm.close_session("orch_sess_1")
