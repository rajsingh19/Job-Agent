import pytest
from pathlib import Path
from app.services.browser.form_parser import FormParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "portals"


class MockLocator:
    def __init__(self, elements):
        self.elements = elements

    async def count(self):
        return len(self.elements)

    def nth(self, idx):
        return MockLocator([self.elements[idx]] if idx < len(self.elements) else [])

    @property
    def first(self):
        return self

    async def is_visible(self):
        return len(self.elements) > 0

    async def inner_text(self):
        return self.elements[0] if self.elements else ""

    async def get_attribute(self, attr):
        return None


class MockDiscoveryPage:
    def __init__(self, url: str, content: str, fields=None, buttons=None):
        self.url = url
        self._content = content
        self._fields = fields or []
        self._buttons = buttons or []

    async def content(self):
        return self._content

    async def evaluate(self, script):
        return self._fields

    def locator(self, selector: str):
        import re
        if ":has-text(" in selector:
            m = re.search(r":has-text\(['\"]([^'\"]+)['\"]\)", selector)
            if m:
                target_text = m.group(1).lower()
                matched = [b for b in self._buttons if target_text in b.lower()]
                return MockLocator(matched)
        if "next" in selector.lower():
            matched = [b for b in self._buttons if "next" in b.lower() or "continue" in b.lower()]
            return MockLocator(matched)
        if "button" in selector.lower() or "submit" in selector.lower():
            return MockLocator(self._buttons)
        return MockLocator([])


@pytest.mark.asyncio
async def test_greenhouse_form_discovery():
    single_step_html = (FIXTURES_DIR / "greenhouse" / "single_step.html").read_text()
    mock_fields = [
        {"field_id": "first_name", "name": "first_name", "label": "First Name *", "input_type": "text", "required": True, "selector": "#first_name"},
        {"field_id": "last_name", "name": "last_name", "label": "Last Name *", "input_type": "text", "required": True, "selector": "#last_name"},
        {"field_id": "email", "name": "email", "label": "Email *", "input_type": "email", "required": True, "selector": "#email"},
        {"field_id": "resume", "name": "resume", "label": "Resume/CV *", "input_type": "file", "required": True, "selector": "#resume"},
    ]
    page = MockDiscoveryPage(
        url="https://boards.greenhouse.io/acme/jobs/123",
        content=single_step_html,
        fields=mock_fields,
        buttons=["Submit Application"],
    )

    discovered = await FormParser.parse_form(page, form_id="test_gh_form")
    assert len(discovered.fields) == 4
    assert discovered.has_submit_button is True
    assert discovered.has_next_button is False
    assert discovered.detected_platform == "greenhouse"


@pytest.mark.asyncio
async def test_greenhouse_multi_step_discovery():
    multi_step_html = (FIXTURES_DIR / "greenhouse" / "multi_step.html").read_text()
    page = MockDiscoveryPage(
        url="https://boards.greenhouse.io/acme/jobs/123/step1",
        content=multi_step_html,
        fields=[],
        buttons=["Next"],
    )

    discovered = await FormParser.parse_form(page, form_id="test_gh_multi")
    assert discovered.step_index == 1
    assert discovered.total_steps == 3
    assert discovered.has_next_button is True
    assert discovered.detected_platform == "greenhouse"
