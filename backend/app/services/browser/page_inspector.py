import logging
from typing import Any, Dict, List, Optional
from app.services.browser.models import BrowserField

logger = logging.getLogger(__name__)

# JS script evaluated in page context to extract visible form fields safely
PAGE_INSPECTION_SCRIPT = """
() => {
    const fields = [];
    const elements = Array.from(document.querySelectorAll('input, select, textarea'));

    elements.forEach((el, index) => {
        const type = (el.tagName.toLowerCase() === 'textarea') ? 'textarea' :
                     (el.tagName.toLowerCase() === 'select') ? 'select' :
                     (el.getAttribute('type') || 'text').toLowerCase();

        // Skip hidden inputs, password fields, and submit buttons from standard field list
        if (type === 'hidden' || type === 'password' || type === 'submit') {
            return;
        }

        // Check visibility
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const visible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';

        // Find label text
        let labelText = '';
        if (el.id) {
            const labelEl = document.querySelector(`label[for="${el.id}"]`);
            if (labelEl) labelText = labelEl.innerText.trim();
        }
        if (!labelText) {
            const parentLabel = el.closest('label');
            if (parentLabel) {
                labelText = parentLabel.innerText.trim();
            }
        }
        if (!labelText && el.getAttribute('aria-label')) {
            labelText = el.getAttribute('aria-label').trim();
        }
        if (!labelText && el.getAttribute('aria-labelledby')) {
            const labelledByEl = document.getElementById(el.getAttribute('aria-labelledby'));
            if (labelledByEl) labelText = labelledByEl.innerText.trim();
        }
        if (!labelText && el.placeholder) {
            labelText = el.placeholder.trim();
        }

        // Extract options for selects
        const options = [];
        if (el.tagName.toLowerCase() === 'select') {
            Array.from(el.querySelectorAll('option')).forEach(opt => {
                const text = opt.innerText.trim() || opt.value.trim();
                if (text) options.push(text);
            });
        }

        // Generate robust selector
        let selector = '';
        if (el.id) {
            selector = `#${el.id}`;
        } else if (el.name) {
            selector = `${el.tagName.toLowerCase()}[name="${el.name}"]`;
        } else {
            selector = `${el.tagName.toLowerCase()}:nth-of-type(${index + 1})`;
        }

        fields.push({
            field_id: el.id || el.name || `field_${index}`,
            name: el.name || null,
            label: labelText || null,
            input_type: type,
            placeholder: el.placeholder || null,
            selector: selector,
            required: el.required || el.getAttribute('aria-required') === 'true',
            options: options,
            visible: visible,
            enabled: !el.disabled,
            value: el.value || null,
            autocomplete: el.getAttribute('autocomplete') || null
        });
    });

    return fields;
}
"""


class PageInspector:
    """
    Inspects DOM of an application page and extracts normalized form fields safely.
    Strictly ignores hidden tokens, credentials, and non-application metadata.
    """

    @classmethod
    async def inspect_fields(cls, page) -> List[BrowserField]:
        """
        Executes safe extraction script on page and returns list of BrowserField models.
        """
        try:
            if hasattr(page, "evaluate"):
                raw_fields: List[Dict[str, Any]] = await page.evaluate(PAGE_INSPECTION_SCRIPT)
            else:
                raw_fields = []

            results: List[BrowserField] = []
            for item in raw_fields:
                try:
                    field = BrowserField(**item)
                    results.append(field)
                except Exception as ex:
                    logger.warning("Failed to deserialize field: %s, error: %s", item, ex)

            return results
        except Exception as e:
            logger.error("Error inspecting page fields: %s", e)
            return []
