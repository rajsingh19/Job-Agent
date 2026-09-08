import pytest
from app.services.browser.auth_detector import AuthDetector
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.enums import AuthStatus


@pytest.mark.asyncio
async def test_auth_detection_login_form():
    """Detects login requirement on a page containing a password input."""
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("auth_test_1", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <h2>Sign in to continue</h2>
                <input type="text" placeholder="Email" />
                <input type="password" placeholder="Password" />
                <button>Sign In</button>
            </body>
        </html>
    """)

    status = await AuthDetector.detect_auth_status(page)
    assert status == AuthStatus.LOGIN_REQUIRED

    await bm.close_session("auth_test_1")


@pytest.mark.asyncio
async def test_auth_detection_authenticated_page():
    """Detects authenticated state on a page with sign out / account indicators."""
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("auth_test_2", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <div>Welcome back, Jane! <a href="/logout">Sign out</a></div>
                <h1>Career Application</h1>
                <input type="text" name="full_name" />
            </body>
        </html>
    """)

    status = await AuthDetector.detect_auth_status(page)
    assert status == AuthStatus.AUTHENTICATED

    await bm.close_session("auth_test_2")
