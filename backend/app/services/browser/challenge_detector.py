import logging
import re
from typing import Optional, Tuple
from app.services.browser.enums import ChallengeType

logger = logging.getLogger(__name__)

# DOM selectors and text regexes for detecting security challenges
CAPTCHA_SELECTORS = [
    'iframe[src*="recaptcha"]',
    'iframe[src*="hcaptcha"]',
    'iframe[src*="turnstile"]',
    'iframe[src*="challenges.cloudflare.com"]',
    'iframe[src*="arkoselabs"]',
    'div.g-recaptcha',
    'div.h-captcha',
    'div.cf-turnstile',
    '[data-sitekey]',
]

BOT_CHECK_TEXTS = [
    re.compile(r"checking\s+your\s+browser\s+before\s+accessing", re.IGNORECASE),
    re.compile(r"verify\s+you\s+are\s+human", re.IGNORECASE),
    re.compile(r"just\s+a\s+moment\.\.\.", re.IGNORECASE),
    re.compile(r"attention\s+required!\s+\|\s+cloudflare", re.IGNORECASE),
    re.compile(r"security\s+check\s+to\s+access", re.IGNORECASE),
    re.compile(r"datadome", re.IGNORECASE),
    re.compile(r"perimeterx", re.IGNORECASE),
]

OTP_TEXTS = [
    re.compile(r"enter\s+(the\s+)?(one-time\s+passcode|otp|verification\s+code)", re.IGNORECASE),
    re.compile(r"we('ve|\s+have)\s+sent\s+a\s+code\s+to", re.IGNORECASE),
    re.compile(r"enter\s+the\s+6-digit\s+code", re.IGNORECASE),
]

TWO_FACTOR_TEXTS = [
    re.compile(r"two-factor\s+authentication", re.IGNORECASE),
    re.compile(r"2-step\s+verification", re.IGNORECASE),
    re.compile(r"authenticator\s+app", re.IGNORECASE),
    re.compile(r"security\s+key", re.IGNORECASE),
]

RATE_LIMIT_TEXTS = [
    re.compile(r"too\s+many\s+requests", re.IGNORECASE),
    re.compile(r"rate\s+limit\s+exceeded", re.IGNORECASE),
    re.compile(r"429\s+too\s+many\s+requests", re.IGNORECASE),
]

ACCESS_DENIED_TEXTS = [
    re.compile(r"access\s+denied", re.IGNORECASE),
    re.compile(r"403\s+forbidden", re.IGNORECASE),
    re.compile(r"you\s+do\s+not\s+have\s+permission\s+to\s+access", re.IGNORECASE),
]


class ChallengeDetector:
    """
    Scans the page for security challenges (CAPTCHA, bot checks, OTP, 2FA, rate limits).
    
    STRICT POLICY: Never attempts to solve, defeat, evade, or bypass any security challenge.
    When a challenge is detected, execution must halt and request manual user action.
    """

    @classmethod
    async def detect_challenge(cls, page) -> Tuple[ChallengeType, Optional[str]]:
        """
        Detects if a challenge is present on the page.
        Returns (ChallengeType, explanation_message).
        """
        try:
            # 1. Check CAPTCHA element selectors
            for selector in CAPTCHA_SELECTORS:
                count = await page.locator(selector).count() if hasattr(page, "locator") else 0
                if count > 0:
                    logger.warning("CAPTCHA element detected via selector: %s", selector)
                    return (
                        ChallengeType.CAPTCHA,
                        "A CAPTCHA challenge was detected. Please complete it manually in the browser session."
                    )

            # 2. Check visible content against regex patterns
            content = await page.content() if hasattr(page, "content") else ""

            for pattern in BOT_CHECK_TEXTS:
                if pattern.search(content):
                    logger.warning("Bot challenge detected via content signature: %s", pattern.pattern)
                    return (
                        ChallengeType.BOT_CHECK,
                        "A bot verification challenge was detected. Please complete it manually in the browser session."
                    )

            for pattern in OTP_TEXTS:
                if pattern.search(content):
                    logger.warning("OTP verification prompt detected: %s", pattern.pattern)
                    return (
                        ChallengeType.OTP_REQUIRED,
                        "A one-time passcode (OTP) verification is required. Please enter it manually in the browser session."
                    )

            for pattern in TWO_FACTOR_TEXTS:
                if pattern.search(content):
                    logger.warning("Two-factor authentication prompt detected: %s", pattern.pattern)
                    return (
                        ChallengeType.TWO_FACTOR_REQUIRED,
                        "Two-factor authentication is required. Please approve the prompt manually in the browser session."
                    )

            for pattern in RATE_LIMIT_TEXTS:
                if pattern.search(content):
                    logger.warning("Rate limit page detected: %s", pattern.pattern)
                    return (
                        ChallengeType.RATE_LIMITED,
                        "The application portal is currently rate-limiting requests. Please wait before retrying."
                    )

            for pattern in ACCESS_DENIED_TEXTS:
                if pattern.search(content):
                    logger.warning("Access denied page detected: %s", pattern.pattern)
                    return (
                        ChallengeType.ACCESS_DENIED,
                        "Access to the application page was denied by the host server."
                    )

            return (ChallengeType.NONE, None)
        except Exception as e:
            logger.error("Error during challenge detection: %s", e)
            return (ChallengeType.NONE, None)
