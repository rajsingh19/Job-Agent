import logging
import re
from typing import List, Optional
from app.services.browser.models import BrowserField, DiscoveredForm
from app.services.browser.page_inspector import PageInspector

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
    Differentiates intermediate step navigation buttons from final submission controls.
    """

    @classmethod
    async def parse_form(cls, page, form_id: str = "app_form") -> DiscoveredForm:
        """
        Parses fields and detects navigation/submission controls on the current page.
        """
        fields: List[BrowserField] = await PageInspector.inspect_fields(page)

        # Inspect buttons
        has_next = False
        has_submit = False

        if hasattr(page, "locator"):
            try:
                # Find all buttons and submit inputs
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

                    # Check next button
                    if any(p.search(text) for p in NEXT_BUTTON_PATTERNS):
                        has_next = True

                    # Check submit button
                    if any(p.search(text) for p in SUBMIT_BUTTON_PATTERNS):
                        has_submit = True
            except Exception as e:
                logger.warning("Error checking form navigation buttons: %s", e)

        # Determine current URL
        action_url = page.url if hasattr(page, "url") else None

        return DiscoveredForm(
            form_id=form_id,
            action_url=action_url,
            fields=fields,
            has_next_button=has_next,
            has_submit_button=has_submit,
        )
