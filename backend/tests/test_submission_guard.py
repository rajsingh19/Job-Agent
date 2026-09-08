import pytest
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.enums import FieldActionType
from app.services.browser.exceptions import SubmissionBlockedError
from app.services.browser.field_executor import FieldExecutor
from app.services.browser.models import FieldExecutionAction


@pytest.mark.asyncio
async def test_submission_guard_blocks_final_submission():
    """
    CRITICAL SECURITY INVARIANT:
    Verifies that Phase 7 strictly prohibits clicking final submit or apply controls,
    raising SubmissionBlockedError at the service layer.
    """
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("guard_test_1", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <form id="apply_form">
                    <input id="name" type="text" />
                    <button id="submit_btn" type="submit">Submit Application</button>
                    <button id="apply_btn">Apply Now</button>
                    <button id="next_btn">Continue</button>
                </form>
            </body>
        </html>
    """)

    # 1. Attempting to click "Submit Application" must raise SubmissionBlockedError
    with pytest.raises(SubmissionBlockedError) as exc_info:
        await FieldExecutor.assert_not_submission_control(page, "#submit_btn")
    assert "Phase 7" in str(exc_info.value) or "Submit" in str(exc_info.value)

    # 2. Attempting to click "Apply Now" must raise SubmissionBlockedError
    with pytest.raises(SubmissionBlockedError):
        await FieldExecutor.assert_not_submission_control(page, "#apply_btn")

    # 3. Intermediate navigation button "Continue" should NOT raise SubmissionBlockedError
    await FieldExecutor.assert_not_submission_control(page, "#next_btn")

    # 4. Attempting to execute CLICK_NEXT on a submit button raises SubmissionBlockedError
    act_malicious = FieldExecutionAction(
        field_id="submit_btn",
        selector="#submit_btn",
        action_type=FieldActionType.CLICK_NEXT,
    )
    with pytest.raises(SubmissionBlockedError):
        await FieldExecutor.execute_action(page, act_malicious)

    await bm.close_session("guard_test_1")
