import logging
import re
from typing import Optional
from app.services.browser.enums import AuthStatus

logger = logging.getLogger(__name__)

LOGIN_URL_PATTERNS = [
    re.compile(r"/login", re.IGNORECASE),
    re.compile(r"/signin", re.IGNORECASE),
    re.compile(r"/sign-in", re.IGNORECASE),
    re.compile(r"/auth/", re.IGNORECASE),
    re.compile(r"/session/new", re.IGNORECASE),
    re.compile(r"/users/sign_in", re.IGNORECASE),
    re.compile(r"/accounts/login", re.IGNORECASE),
]

AUTHENTICATED_INDICATORS = [
    re.compile(r"\b(sign\s*out|log\s*out)\b", re.IGNORECASE),
    re.compile(r"\b(my\s*account|profile\s*settings|view\s*profile)\b", re.IGNORECASE),
]

LOGIN_TEXT_INDICATORS = [
    re.compile(r"\b(sign\s*in|log\s*in|login\s*to\s*apply)\b", re.IGNORECASE),
    re.compile(r"\b(enter\s*your\s*password)\b", re.IGNORECASE),
]


class AuthDetector:
    """
    Detects whether an application page requires authentication or is already authenticated.
    Never attempts to bypass authentication or intercept user credentials.
    """

    @classmethod
    async def detect_auth_status(cls, page) -> AuthStatus:
        """
        Inspects page URL, DOM inputs, and visible text to evaluate authentication state.
        Works with Playwright Page or mock page object.
        """
        try:
            url = page.url if hasattr(page, "url") else ""

            # 1. Check URL patterns
            for pattern in LOGIN_URL_PATTERNS:
                if pattern.search(url):
                    logger.info("Login required detected by URL pattern: %s", url)
                    return AuthStatus.LOGIN_REQUIRED

            # 2. Check for password input field in DOM
            password_inputs = await page.locator('input[type="password"]').count() if hasattr(page, "locator") else 0
            if password_inputs > 0:
                logger.info("Login required detected by password input presence")
                return AuthStatus.LOGIN_REQUIRED

            # 3. Check for sign out / authenticated markers
            content = await page.content() if hasattr(page, "content") else ""
            for pattern in AUTHENTICATED_INDICATORS:
                if pattern.search(content):
                    return AuthStatus.AUTHENTICATED

            # 4. Check for login text if on an ambiguous landing page
            for pattern in LOGIN_TEXT_INDICATORS:
                if pattern.search(content):
                    # Check if there is an explicit sign in button or link
                    login_buttons = await page.locator(
                        'button:has-text("Sign in"), button:has-text("Log in"), a:has-text("Sign in"), a:has-text("Log in")'
                    ).count() if hasattr(page, "locator") else 0
                    if login_buttons > 0:
                        return AuthStatus.LOGIN_REQUIRED

            return AuthStatus.UNKNOWN
        except Exception as e:
            logger.warning("Error detecting authentication status: %s", e)
            return AuthStatus.UNKNOWN
