import pytest
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.form_parser import FormParser


@pytest.mark.asyncio
async def test_form_parser_extraction_and_buttons():
    """Verifies that FormParser correctly parses DOM fields, select options, and action buttons."""
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("form_test_1", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <form id="job_application" action="/apply">
                    <label for="first_name">First Name</label>
                    <input id="first_name" name="first_name" type="text" required />

                    <label for="user_email">Email Address</label>
                    <input id="user_email" name="email" type="email" required />

                    <label for="user_role">Target Role</label>
                    <select id="user_role" name="role">
                        <option value="fe">Frontend Engineer</option>
                        <option value="be">Backend Engineer</option>
                    </select>

                    <label for="resume_file">Upload Resume</label>
                    <input id="resume_file" name="resume" type="file" />

                    <button type="button">Next Step</button>
                    <button type="submit">Submit Application</button>
                </form>
            </body>
        </html>
    """)

    discovered = await FormParser.parse_form(page, form_id="job_application")
    assert discovered.form_id == "job_application"
    assert len(discovered.fields) == 4

    # Verify field 1: first name
    fn = next(f for f in discovered.fields if f.field_id == "first_name")
    assert fn.label == "First Name"
    assert fn.input_type == "text"
    assert fn.required is True

    # Verify field 3: select
    role_field = next(f for f in discovered.fields if f.field_id == "user_role")
    assert role_field.input_type == "select"
    assert "Frontend Engineer" in role_field.options

    # Verify button detection
    assert discovered.has_next_button is True
    assert discovered.has_submit_button is True

    await bm.close_session("form_test_1")
