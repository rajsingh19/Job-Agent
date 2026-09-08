import logging
import re
from typing import List, Optional
from app.services.browser.models import BrowserField, DiscoveredForm
from app.services.browser.page_inspector import PageInspector
from app.services.portal.registry import PortalRegistry

logger = logging.getLogger(__name__)

NEXT_BUTTON_PATTERNS = [
    re.compile(r"^\s*(next|continue|save\s*&\s*continue|next\s*step|proceed)\s*$", re.IGNORECASE),
    re.compile(r"continue\s*to\s*", re.IGNORECASE),
]

SUBMIT_BUTTON_PATTERNS = [
    re.compile(r"^\s*(submit|submit\s*application|apply|apply\s*now|send\s*application|complete\s*application|finish)\s*$", re.IGNORECASE),
    re.compile(r"submit\s*your\s*application", re.IGNORECASE),
]


class FormParser:
    """
    Parses application page content and DOM structure into a normalized DiscoveredForm.
    Differentiates intermediate step navigation buttons from final submission controls,
    leveraging portal-specific adapters and global fallback patterns.
    """

    @classmethod
    async def parse_form(cls, page, form_id: str = "app_form") -> DiscoveredForm:
        """
        Parses fields and detects navigation/submission controls on the current page.
        """
        url = page.url if hasattr(page, "url") else None
        fields: List[BrowserField] = await PageInspector.inspect_fields(page)

        # Retrieve portal adapter if matching
        registry = PortalRegistry.get_instance()
        adapter = registry.get_adapter_for_url(url or "") if url else registry._fallback_adapter

        # Detect step information
        step_info = await adapter.detect_current_step(page)
        has_next = step_info.has_next
        has_submit = step_info.has_submit

        if hasattr(page, "locator"):
            try:
                # Supplementary inspection via text patterns if not yet found
                if not has_next or not has_submit:
                    button_locators = page.locator('button, input[type="submit"], a[role="button"]')
                    count = await button_locators.count()

                    for i in range(count):
                        btn = button_locators.nth(i)
                        if not await btn.is_visible():
                            continue

                        text = (await btn.inner_text()).strip() if hasattr(btn, "inner_text") else ""
                        if not text:
                            val = await btn.get_attribute("value") or ""
                            text = val.strip()

                        if not has_next and any(p.search(text) for p in NEXT_BUTTON_PATTERNS):
                            has_next = True

                        if not has_submit and any(p.search(text) for p in SUBMIT_BUTTON_PATTERNS):
                            has_submit = True
            except Exception as e:
                logger.warning("Error checking form navigation buttons: %s", e)

        return DiscoveredForm(
            form_id=form_id,
            action_url=url,
            fields=fields,
            step_index=step_info.step_index,
            total_steps=step_info.total_steps,
            has_next_button=has_next,
            has_submit_button=has_submit,
            detected_platform=adapter.portal_id if adapter else None,
        )
