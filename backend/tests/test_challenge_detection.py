import pytest
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.challenge_detector import ChallengeDetector
from app.services.browser.enums import ChallengeType


@pytest.mark.asyncio
async def test_challenge_detection_captcha():
    """Detects CAPTCHA container without attempting bypass."""
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("chal_test_1", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <h1>Security Check</h1>
                <div class="g-recaptcha" data-sitekey="test-key"></div>
            </body>
        </html>
    """)

    chal_type, msg = await ChallengeDetector.detect_challenge(page)
    assert chal_type == ChallengeType.CAPTCHA
    assert "CAPTCHA" in msg

    await bm.close_session("chal_test_1")


@pytest.mark.asyncio
async def test_challenge_detection_bot_check():
    """Detects Cloudflare bot verification text."""
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("chal_test_2", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <p>Checking your browser before accessing the website...</p>
                <p>Please wait a moment.</p>
            </body>
        </html>
    """)

    chal_type, msg = await ChallengeDetector.detect_challenge(page)
    assert chal_type == ChallengeType.BOT_CHECK
    assert "bot" in msg.lower()

    await bm.close_session("chal_test_2")


@pytest.mark.asyncio
async def test_challenge_detection_otp():
    """Detects one-time passcode prompt."""
    bm = await BrowserManager.get_instance()
    sess = await bm.create_session("chal_test_3", "user_1")
    page = sess.page

    await page.set_content("""
        <html>
            <body>
                <h2>Verification Required</h2>
                <p>Enter the one-time passcode sent to your phone</p>
                <input type="text" name="otp" />
            </body>
        </html>
    """)

    chal_type, msg = await ChallengeDetector.detect_challenge(page)
    assert chal_type == ChallengeType.OTP_REQUIRED
    assert "passcode" in msg.lower() or "otp" in msg.lower()

    await bm.close_session("chal_test_3")
