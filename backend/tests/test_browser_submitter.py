from datetime import datetime, timezone
import pytest
from app.services.browser.browser_manager import BrowserManager
from app.services.submission.browser_submitter import BrowserSubmitter
from app.services.submission.exceptions import (
    SubmissionBlockedError,
    SubmissionControlNotFoundError,
)
from app.services.submission.models import ConfirmationStatus, SubmissionAuthorization


@pytest.mark.asyncio
async def test_browser_submitter_blocks_missing_authorization():
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("submitter_test_1", "user_1")
    page = sess.page

    # Pass None as authorization
    with pytest.raises(SubmissionBlockedError):
        await BrowserSubmitter.submit(
            page=page,
            authorization=None,
            application_id="app_123",
        )

    await bm.close_session("submitter_test_1")


@pytest.mark.asyncio
async def test_browser_submitter_blocks_cross_application_token():
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("submitter_test_2", "user_1")
    page = sess.page

    auth = SubmissionAuthorization(
        application_id="app_OTHER",
        user_id="user_1",
        approved_version_hash="hash123",
        approved_at=datetime.now(timezone.utc),
        token="appr_token_valid",
    )

    with pytest.raises(SubmissionBlockedError):
        await BrowserSubmitter.submit(
            page=page,
            authorization=auth,
            application_id="app_TARGET",
        )

    await bm.close_session("submitter_test_2")


@pytest.mark.asyncio
async def test_browser_submitter_control_not_found():
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("submitter_test_3", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <div>No submit buttons here!</div>
            </body>
        </html>
    """)

    auth = SubmissionAuthorization(
        application_id="app_123",
        user_id="user_1",
        approved_version_hash="hash123",
        approved_at=datetime.now(timezone.utc),
        token="appr_token_valid",
    )

    with pytest.raises(SubmissionControlNotFoundError):
        await BrowserSubmitter.submit(
            page=page,
            authorization=auth,
            application_id="app_123",
        )

    await bm.close_session("submitter_test_3")


@pytest.mark.asyncio
async def test_browser_submitter_successful_click_and_confirmation():
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("submitter_test_4", "user_1")
    page = sess.page

    # Page with submit button that changes DOM to thank-you upon click
    await page.set_content("""
        <html>
            <body>
                <div id="content">
                    <h1>Job Application</h1>
                    <button id="submit_btn" type="submit" onclick="document.getElementById('content').innerHTML='<h1>Thank you for applying!</h1><p>Your application was submitted.</p><p>Confirmation #: CONF-9911</p>'">Submit Application</button>
                </div>
            </body>
        </html>
    """)

    auth = SubmissionAuthorization(
        application_id="app_123",
        user_id="user_1",
        approved_version_hash="hash123",
        approved_at=datetime.now(timezone.utc),
        token="appr_token_valid",
    )

    result = await BrowserSubmitter.submit(
        page=page,
        authorization=auth,
        application_id="app_123",
    )

    assert result.status == ConfirmationStatus.CONFIRMED
    assert result.confirmation_reference == "CONF-9911"
    assert result.screenshot_id is not None

    await bm.close_session("submitter_test_4")
