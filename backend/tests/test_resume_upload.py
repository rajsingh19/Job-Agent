import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.resume import Resume
from app.models.user import User
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.exceptions import ResumeUploadError
from app.services.browser.resume_uploader import ResumeUploader


@pytest.mark.asyncio
async def test_resume_uploader_success_and_security(db_session: AsyncSession):
    """Verifies that ResumeUploader enforces ownership, file validity, and path containment."""
    settings = get_settings()

    # 1. Create User A and Resume A
    user_a = User(email="upload_user_a@example.com")
    db_session.add(user_a)
    await db_session.flush()

    resumes_dir = settings.resumes_dir.resolve()
    real_file_path = resumes_dir / f"{user_a.id}_resume.pdf"
    real_file_path.write_bytes(b"%PDF-1.4 test resume content")

    resume_a = Resume(
        user_id=user_a.id,
        name="test_resume.pdf",
        file_reference=str(real_file_path),
        content_hash="test_content_hash_a",
        parsed_profile={"skills": ["Python"]},
    )
    db_session.add(resume_a)
    await db_session.commit()

    # 2. Setup browser page with file input
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("upload_test_1", user_a.id)
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <input id="resume_upload" type="file" />
            </body>
        </html>
    """)

    # 3. Successful upload for User A
    uploaded = await ResumeUploader.upload_resume(
        page=page,
        db=db_session,
        user_id=user_a.id,
        resume_id=resume_a.id,
        selector="#resume_upload",
    )
    assert uploaded is True

    # 4. Attempt upload by User B (unauthorized) -> must fail
    with pytest.raises(ResumeUploadError) as exc_info:
        await ResumeUploader.upload_resume(
            page=page,
            db=db_session,
            user_id="unauthorized_user_b",
            resume_id=resume_a.id,
            selector="#resume_upload",
        )
    assert "unauthorized" in str(exc_info.value).lower()

    # 5. Path traversal attempt -> must fail
    resume_traversal = Resume(
        user_id=user_a.id,
        name="evil.pdf",
        file_reference="/etc/passwd",
        content_hash="test_hash_evil",
    )
    db_session.add(resume_traversal)
    await db_session.commit()

    with pytest.raises(ResumeUploadError):
        await ResumeUploader.upload_resume(
            page=page,
            db=db_session,
            user_id=user_a.id,
            resume_id=resume_traversal.id,
            selector="#resume_upload",
        )

    await bm.close_session("upload_test_1")
