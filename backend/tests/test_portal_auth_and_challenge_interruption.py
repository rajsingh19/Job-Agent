import pytest
from pathlib import Path
from app.services.browser.auth_detector import AuthDetector
from app.services.browser.challenge_detector import ChallengeDetector
from app.services.browser.enums import AuthStatus, ChallengeType

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "portals" / "generic"


class MockLocator:
    def __init__(self, count_val=0):
        self._count = count_val

    async def count(self):
        return self._count


class MockAuthChallengePage:
    def __init__(self, url: str, content: str, password_count: int = 0, captcha_count: int = 0):
        self.url = url
        self._content = content
        self.password_count = password_count
        self.captcha_count = captcha_count

    async def content(self):
        return self._content

    def locator(self, selector: str):
        if "password" in selector:
            return MockLocator(self.password_count)
        if any(c in selector for c in ["turnstile", "recaptcha", "hcaptcha"]):
            return MockLocator(self.captcha_count)
        return MockLocator(0)


@pytest.mark.asyncio
async def test_auth_detection_login_required():
    login_html = (FIXTURES_DIR / "login_required.html").read_text()
    page = MockAuthChallengePage(
        url="https://careers.enterprise.com/auth/login",
        content=login_html,
        password_count=1,
    )

    status = await AuthDetector.detect_auth_status(page)
    assert status == AuthStatus.LOGIN_REQUIRED


@pytest.mark.asyncio
async def test_challenge_detection_captcha():
    captcha_html = (FIXTURES_DIR / "captcha.html").read_text()
    page = MockAuthChallengePage(
        url="https://careers.enterprise.com/apply",
        content=captcha_html,
        captcha_count=1,
    )

    ctype, msg = await ChallengeDetector.detect_challenge(page)
    assert ctype in (ChallengeType.CAPTCHA, ChallengeType.BOT_CHECK)
    assert msg is not None


@pytest.mark.asyncio
async def test_challenge_detection_otp():
    otp_html = (FIXTURES_DIR / "otp.html").read_text()
    page = MockAuthChallengePage(
        url="https://careers.enterprise.com/auth/verify-otp",
        content=otp_html,
    )

    ctype, msg = await ChallengeDetector.detect_challenge(page)
    assert ctype == ChallengeType.OTP_REQUIRED
    assert "one-time passcode" in msg.lower() or "verification" in msg.lower()
