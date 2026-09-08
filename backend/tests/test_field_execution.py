import pytest
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.enums import FieldActionType
from app.services.browser.field_executor import FieldExecutor
from app.services.browser.models import FieldExecutionAction


@pytest.mark.asyncio
async def test_field_execution_fill_and_select():
    """Verifies that FieldExecutor fills inputs and selects options accurately in the DOM."""
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("exec_test_1", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <input id="candidate_name" type="text" />
                <select id="country">
                    <option value="CA">Canada</option>
                    <option value="US">United States</option>
                </select>
                <input id="agree_terms" type="checkbox" />
            </body>
        </html>
    """)

    # 1. Execute FILL
    act_fill = FieldExecutionAction(
        field_id="candidate_name",
        selector="#candidate_name",
        action_type=FieldActionType.FILL,
        value="Grace Hopper",
    )
    res_fill = await FieldExecutor.execute_action(page, act_fill)
    assert res_fill is True
    val = await page.input_value("#candidate_name")
    assert val == "Grace Hopper"

    # 2. Execute SELECT
    act_sel = FieldExecutionAction(
        field_id="country",
        selector="#country",
        action_type=FieldActionType.SELECT,
        value="United States",
    )
    res_sel = await FieldExecutor.execute_action(page, act_sel)
    assert res_sel is True
    sel_val = await page.input_value("#country")
    assert sel_val == "US"

    # 3. Execute CHECK
    act_chk = FieldExecutionAction(
        field_id="agree_terms",
        selector="#agree_terms",
        action_type=FieldActionType.CHECK,
        value="true",
    )
    res_chk = await FieldExecutor.execute_action(page, act_chk)
    assert res_chk is True
    is_checked = await page.is_checked("#agree_terms")
    assert is_checked is True

    # 4. Skip action when requires_user_input is True
    act_skip = FieldExecutionAction(
        field_id="sensitive_field",
        selector="#candidate_name",
        action_type=FieldActionType.FILL,
        value="Some Answer",
        requires_user_input=True,
    )
    res_skip = await FieldExecutor.execute_action(page, act_skip)
    assert res_skip is False

    await bm.close_session("exec_test_1")
