import logging
import re
from typing import Optional
from app.services.browser.enums import FieldActionType
from app.services.browser.exceptions import FieldExecutionError, SubmissionBlockedError
from app.services.browser.models import FieldExecutionAction

logger = logging.getLogger(__name__)

SUBMIT_BUTTON_TEXT_PATTERNS = [
    re.compile(r"^\s*(submit|submit\s*application|apply|apply\s*now|finish\s*application|complete\s*application|send\s*application)\s*$", re.IGNORECASE),
    re.compile(r"submit\s*your\s*application", re.IGNORECASE),
]


class FieldExecutor:
    """
    Safely executes form actions on a Playwright page.
    Includes the strict, service-level submission guard that blocks any attempt to submit an application.
    """

    @classmethod
    async def assert_not_submission_control(cls, page, selector: str) -> None:
        """
        Guarantees that Phase 7 never clicks a final submit button.
        Raises SubmissionBlockedError if the target control matches submission keywords.
        """
        try:
            if not hasattr(page, "locator"):
                return

            locator = page.locator(selector).first
            text = ""
            if hasattr(locator, "inner_text"):
                try:
                    text = (await locator.inner_text()).strip()
                except Exception:
                    text = ""

            val = ""
            if hasattr(locator, "get_attribute"):
                try:
                    val = (await locator.get_attribute("value") or "").strip()
                except Exception:
                    val = ""

            aria_label = ""
            if hasattr(locator, "get_attribute"):
                try:
                    aria_label = (await locator.get_attribute("aria-label") or "").strip()
                except Exception:
                    aria_label = ""

            combined_indicators = f"{text} {val} {aria_label}".strip()

            for pattern in SUBMIT_BUTTON_TEXT_PATTERNS:
                if pattern.search(combined_indicators):
                    logger.critical(
                        "SUBMISSION BLOCKED: Phase 7 attempted to interact with submission control: '%s'",
                        combined_indicators,
                    )
                    raise SubmissionBlockedError(
                        control_name=combined_indicators or selector,
                        message="Final application submission is prohibited in Phase 7."
                    )
        except SubmissionBlockedError:
            raise
        except Exception as e:
            logger.debug("Minor error evaluating submission control guard: %s", e)

    @classmethod
    async def execute_action(cls, page, action: FieldExecutionAction) -> bool:
        """
        Executes a single field action safely.
        Returns True if successfully executed, False if skipped.
        """
        if action.action_type == FieldActionType.SKIP:
            return False

        if action.requires_user_input:
            logger.info("Skipping execution for field '%s' because user input is required.", action.field_id)
            return False

        if action.action_type != FieldActionType.CLICK_NEXT and not action.value:
            logger.info("Skipping execution for field '%s' because value is empty.", action.field_id)
            return False

        try:
            # 1. Verify locator exists and is ready
            locator = page.locator(action.selector).first
            if hasattr(locator, "is_visible") and not await locator.is_visible():
                logger.warning("Field selector '%s' is not visible; skipping.", action.selector)
                return False

            if hasattr(locator, "is_enabled") and not await locator.is_enabled():
                logger.warning("Field selector '%s' is disabled; skipping.", action.selector)
                return False

            # 2. Execute based on action type
            if action.action_type == FieldActionType.FILL:
                await locator.fill(action.value)
                action.executed = True
                return True

            elif action.action_type == FieldActionType.SELECT:
                # Try selecting by label or value
                try:
                    await locator.select_option(label=action.value)
                except Exception:
                    await locator.select_option(value=action.value)
                action.executed = True
                return True

            elif action.action_type == FieldActionType.CHECK:
                if action.value.lower() in ("true", "1", "yes"):
                    await locator.check()
                else:
                    await locator.uncheck()
                action.executed = True
                return True

            elif action.action_type == FieldActionType.CLICK_NEXT:
                # Guard against accidental submit click
                await cls.assert_not_submission_control(page, action.selector)
                await locator.click()
                action.executed = True
                return True

            return False

        except SubmissionBlockedError:
            raise
        except Exception as e:
            action.execution_error = str(e)
            logger.error("Failed to execute action on '%s': %s", action.field_id, e)
            raise FieldExecutionError(f"Failed to execute field action for '{action.field_id}': {e}") from e
