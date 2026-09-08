import logging
import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple
from app.services.browser.models import BrowserField, DiscoveredForm
from app.services.browser.page_inspector import PageInspector
from app.services.portal.models import FormStepInfo, PortalCapabilities, PortalConfig
from app.services.submission.models import ConfirmationStatus

logger = logging.getLogger(__name__)


class PortalAdapter(ABC):
    """
    Abstract Base Class for ATS and job portal compatibility adapters.
    Encapsulates portal-specific discovery, navigation, field extraction, and confirmation rules.
    """

    def __init__(self, config: PortalConfig, capabilities: PortalCapabilities):
        self.config = config
        self._capabilities = capabilities

    @property
    def portal_id(self) -> str:
        return self.config.portal_id

    @property
    def name(self) -> str:
        return self.config.name

    def capabilities(self) -> PortalCapabilities:
        return self._capabilities

    def get_config(self) -> PortalConfig:
        return self.config

    def matches(self, url: str) -> bool:
        """
        Determines whether the given URL belongs to this portal adapter based on domain regexes.
        """
        if not url:
            return False
        for pattern in self.config.domain_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    async def detect_current_step(self, page: Any) -> FormStepInfo:
        """
        Detects the current step in multi-step or single-step application forms.
        """
        has_next = await self.find_next_control(page) is not None
        has_submit = await self.find_submit_control(page) is not None
        
        # Check for progress indicators / steps in DOM
        step_index = 1
        total_steps = None
        step_label = None

        if hasattr(page, "content"):
            try:
                content = await page.content()
                # Detect "Step X of Y" patterns
                step_match = re.search(r"step\s+(\d+)\s+of\s+(\d+)", content, re.IGNORECASE)
                if step_match:
                    step_index = int(step_match.group(1))
                    total_steps = int(step_match.group(2))
                    step_label = f"Step {step_index} of {total_steps}"
            except Exception as e:
                logger.debug("Could not parse step indicators from content: %s", e)

        return FormStepInfo(
            step_index=step_index,
            total_steps=total_steps,
            step_label=step_label,
            has_next=has_next,
            has_previous=False,
            has_submit=has_submit,
            is_final_step=has_submit and not has_next,
        )

    async def inspect_form(self, page: Any, form_id: str = "portal_form") -> DiscoveredForm:
        """
        Inspects fields and discovers structure on the current page using PageInspector
        supplemented by portal-specific selector aliases.
        """
        fields: List[BrowserField] = await PageInspector.inspect_fields(page)
        step_info = await self.detect_current_step(page)

        action_url = page.url if hasattr(page, "url") else None

        return DiscoveredForm(
            form_id=form_id,
            action_url=action_url,
            fields=fields,
            step_index=step_info.step_index,
            total_steps=step_info.total_steps,
            has_next_button=step_info.has_next,
            has_submit_button=step_info.has_submit,
            detected_platform=self.portal_id,
        )

    async def find_next_control(self, page: Any) -> Optional[Any]:
        """
        Finds the Next / Continue button if present.
        """
        if not hasattr(page, "locator"):
            return None

        for selector in self.config.next_selectors:
            try:
                loc = page.locator(selector).first
                if await loc.count() > 0 and await loc.is_visible():
                    return loc
            except Exception:
                continue
        return None

    async def find_submit_control(self, page: Any) -> Optional[Any]:
        """
        Finds the final Submit button if present.
        """
        if not hasattr(page, "locator"):
            return None

        for selector in self.config.submit_selectors:
            try:
                loc = page.locator(selector).first
                if await loc.count() > 0 and await loc.is_visible():
                    return loc
            except Exception:
                continue
        return None

    async def detect_confirmation(
        self,
        page: Any,
    ) -> Tuple[ConfirmationStatus, Optional[str], Optional[str], List[str]]:
        """
        Inspects page URL and visible DOM for submission confirmation.
        Returns (status, confirmation_type, reference_code, warnings).
        """
        warnings: List[str] = []
        url = page.url if hasattr(page, "url") else ""
        content = await page.content() if hasattr(page, "content") else ""

        # 1. Check error indicators first
        for err_selector in self.config.error_selectors:
            try:
                if hasattr(page, "locator"):
                    loc = page.locator(err_selector)
                    if await loc.count() > 0 and await loc.first.is_visible():
                        return (
                            ConfirmationStatus.NOT_CONFIRMED,
                            "PORTAL_FORM_ERROR",
                            None,
                            [f"Portal validation error detected via selector '{err_selector}'."],
                        )
            except Exception:
                continue

        # 2. Check reference codes
        ref_code: Optional[str] = None
        for ref_pattern in self.config.confirmation_ref_patterns:
            match = re.search(ref_pattern, content, re.IGNORECASE)
            if match:
                ref_code = match.group(1).strip()
                break

        # 3. Check text patterns
        matched_text = False
        for pattern in self.config.confirmation_text_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                matched_text = True
                break

        # 4. Check URL patterns
        matched_url = False
        for url_pattern in self.config.confirmation_url_patterns:
            if re.search(url_pattern, url, re.IGNORECASE):
                matched_url = True
                break

        if matched_url and matched_text:
            return (
                ConfirmationStatus.CONFIRMED,
                "URL_AND_DOM_TEXT_CONFIRMED",
                ref_code,
                warnings,
            )
        elif matched_text:
            return (
                ConfirmationStatus.CONFIRMED,
                "DOM_TEXT_CONFIRMED",
                ref_code,
                warnings,
            )
        elif matched_url:
            return (
                ConfirmationStatus.CONFIRMED,
                "URL_REDIRECT_CONFIRMED",
                ref_code,
                warnings,
            )

        return (
            ConfirmationStatus.UNKNOWN,
            "UNCONFIRMED_STATE",
            None,
            ["No conclusive confirmation banner or redirect detected for portal."],
        )
