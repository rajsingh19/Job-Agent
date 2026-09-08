import logging
import urllib.parse
from app.config import get_settings
from app.services.browser.exceptions import BrowserExecutionError, SubmissionBlockedError
from app.services.browser.field_executor import FieldExecutor

logger = logging.getLogger(__name__)


class NavigationHelper:
    """
    Manages safe URL navigation and multi-step page progression.
    Guards against SSRF/unsupported schemes and accidental submission button clicks.
    """

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        Validates target URL scheme. Only http and https are permitted.
        """
        if not url:
            return False
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            logger.warning("Rejected navigation to forbidden URL scheme: %s", parsed.scheme)
            return False
        return True

    @classmethod
    async def navigate_to_url(cls, page, url: str) -> None:
        """
        Navigates page to target URL safely with timeout settings.
        """
        if not cls.validate_url(url):
            raise BrowserExecutionError(f"Invalid or untrusted application URL: '{url}'")

        settings = get_settings()
        timeout = settings.browser_navigation_timeout_ms

        logger.info("Navigating to application URL: %s (timeout: %dms)", url, timeout)
        try:
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        except Exception as e:
            logger.error("Navigation failed for URL '%s': %s", url, e)
            raise BrowserExecutionError(f"Failed to navigate to application URL: {e}") from e

    @classmethod
    async def click_next_step(cls, page, selector: str) -> None:
        """
        Clicks an intermediate step progression button (e.g. Next, Continue).
        STRICTLY asserts that the targeted element is not a final submission control.
        """
        await FieldExecutor.assert_not_submission_control(page, selector)

        settings = get_settings()
        timeout = settings.browser_timeout_ms

        logger.info("Progressing to next step with selector: %s", selector)
        try:
            locator = page.locator(selector).first
            await locator.click(timeout=timeout)
            await page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except SubmissionBlockedError:
            raise
        except Exception as e:
            logger.error("Failed to click step progression button: %s", e)
            raise BrowserExecutionError(f"Failed to advance form step: {e}") from e

    @classmethod
    async def wait_for_page_stability(cls, page, timeout_ms: int = 5000) -> None:
        """
        Waits for DOM and network to stabilize after a step progression action.
        """
        try:
            if hasattr(page, "wait_for_load_state"):
                await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
        try:
            if hasattr(page, "wait_for_load_state"):
                await page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 3000))
        except Exception:
            pass
