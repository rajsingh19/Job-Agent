import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.services.browser.challenge_detector import ChallengeDetector
from app.services.browser.enums import ChallengeType
from app.services.browser.screenshot_manager import ScreenshotManager
from app.services.submission.confirmation import SubmissionConfirmationDetector
from app.services.submission.exceptions import (
    SubmissionBlockedError,
    SubmissionControlNotFoundError,
)
from app.services.submission.models import (
    ConfirmationStatus,
    SubmissionAuthorization,
    SubmissionResult,
)

logger = logging.getLogger(__name__)

FINAL_SUBMIT_SELECTORS = [
    'button:has-text("Submit Application")',
    'button:has-text("Submit application")',
    'button:has-text("Submit")',
    'input[type="submit"]',
    'button[type="submit"]',
    'button:has-text("Send Application")',
    'button:has-text("Complete Application")',
    'button:has-text("Finish Application")',
    'button:has-text("Apply Now")',
    '[data-testid*="submit"]',
    'button[id*="submit"]',
]


class BrowserSubmitter:
    """
    CRITICAL COMPONENT:
    The ONLY component in the codebase authorized to click the final submit button.
    Enforces authorization token check, captures pre/post submission visual checkpoints,
    identifies the submission control, executes the click, and delegates to
    SubmissionConfirmationDetector.
    """

    @classmethod
    async def submit(
        cls,
        page: any,
        authorization: SubmissionAuthorization,
        application_id: str,
    ) -> SubmissionResult:
        """
        Executes the final application submission on the browser page.
        
        Requires a cryptographically bound SubmissionAuthorization token.
        """
        # 1. Strict authorization guard check
        if not authorization or not authorization.token or not authorization.approved_version_hash:
            raise SubmissionBlockedError(
                "Submission action blocked: Missing or invalid SubmissionAuthorization."
            )
        if authorization.application_id != application_id:
            raise SubmissionBlockedError(
                f"Submission action blocked: Token belongs to application '{authorization.application_id}', not '{application_id}'."
            )

        logger.info(
            f"Executing final submission for application '{application_id}' with auth token '{authorization.token}'."
        )

        # 2. Check for security challenge
        challenge_type, challenge_msg = await ChallengeDetector.detect_challenge(page)
        if challenge_type != ChallengeType.NONE:
            logger.warning(f"Challenge detected on submission page: {challenge_type}")
            return SubmissionResult(
                status=ConfirmationStatus.NOT_CONFIRMED,
                warnings=[f"Challenge detected: {challenge_msg}"],
            )

        # 3. Capture pre-submission visual checkpoint
        pre_screenshot = await ScreenshotManager.capture_checkpoint(
            page=page,
            step="before_final_submission",
            application_id=application_id,
        )

        # 4. Identify final submission control
        submit_button = None
        for selector in FINAL_SUBMIT_SELECTORS:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0 and await locator.is_visible():
                    submit_button = locator
                    logger.info(f"Identified submission control via selector: {selector}")
                    break
            except Exception:
                continue

        if not submit_button:
            try:
                from app.services.portal.registry import PortalRegistry
                adapter = PortalRegistry.get_instance().get_adapter_for_url(page.url if hasattr(page, "url") else "")
                submit_button = await adapter.find_submit_control(page)
                if submit_button:
                    logger.info(f"Identified submission control via adapter '{adapter.portal_id}'")
            except Exception as e:
                logger.debug(f"Portal adapter lookup for submit control failed: {e}")

        if not submit_button:
            logger.error(f"No submission control found on page for application '{application_id}'.")
            raise SubmissionControlNotFoundError(
                f"Final submission control was not found on the page for application '{application_id}'."
            )

        # 5. Click the submit button
        try:
            await submit_button.scroll_into_view_if_needed()
            await submit_button.click()
            logger.info("Final submit button clicked. Waiting for page navigation/idle...")
        except Exception as e:
            logger.error(f"Error clicking submission button: {e}")
            raise

        # 6. Wait for network / navigation
        try:
            if hasattr(page, "wait_for_load_state"):
                await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            # Some portals don't reach pure network idle; short wait
            await asyncio.sleep(2)

        await asyncio.sleep(1)

        # 7. Capture post-submission screenshot
        post_screenshot = await ScreenshotManager.capture_checkpoint(
            page=page,
            step="after_final_submission",
            application_id=application_id,
        )

        # 8. Detect confirmation
        status, conf_type, conf_ref, warnings = await SubmissionConfirmationDetector.detect_from_page(page)

        # 9. Capture outcome checkpoint
        outcome_step = "submission_confirmed" if status == ConfirmationStatus.CONFIRMED else "submission_unknown"
        outcome_screenshot = await ScreenshotManager.capture_checkpoint(
            page=page,
            step=outcome_step,
            application_id=application_id,
        )

        screenshot_id = None
        if outcome_screenshot:
            screenshot_id = outcome_screenshot.id
        elif post_screenshot:
            screenshot_id = post_screenshot.id
        elif pre_screenshot:
            screenshot_id = pre_screenshot.id

        url = page.url if hasattr(page, "url") else None

        return SubmissionResult(
            status=status,
            submitted_at=datetime.now(timezone.utc),
            confirmation_type=conf_type,
            confirmation_reference=conf_ref,
            confirmation_url=url,
            screenshot_id=screenshot_id,
            warnings=warnings,
        )
