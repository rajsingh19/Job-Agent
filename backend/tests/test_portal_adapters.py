import pytest
from pathlib import Path
from app.services.portal.adapters.ashby import AshbyPortalAdapter
from app.services.portal.adapters.generic_ats import GenericATSPortalAdapter
from app.services.portal.adapters.greenhouse import GreenhousePortalAdapter
from app.services.portal.adapters.lever import LeverPortalAdapter
from app.services.submission.models import ConfirmationStatus

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "portals"


class MockLocator:
    def __init__(self, elements):
        self.elements = elements

    async def count(self):
        return len(self.elements)

    @property
    def first(self):
        return self

    async def is_visible(self):
        return len(self.elements) > 0

    async def inner_text(self):
        return self.elements[0] if self.elements else ""

    async def get_attribute(self, attr):
        return None

    async def click(self):
        pass


class MockPortalPage:
    def __init__(self, url: str, content: str, elements=None):
        self.url = url
        self._content = content
        self.elements = elements or {}

    async def content(self):
        return self._content

    async def inner_text(self, selector: str, timeout: int = 5000):
        return self._content

    def locator(self, selector: str):
        for sel_key, elems in self.elements.items():
            if sel_key.lower() in selector.lower():
                return MockLocator(elems)
        return MockLocator([])


@pytest.mark.asyncio
async def test_greenhouse_adapter_confirmation():
    adapter = GreenhousePortalAdapter()
    assert adapter.matches("https://boards.greenhouse.io/acme/jobs/123") is True
    assert adapter.matches("https://lever.co") is False

    conf_html = (FIXTURES_DIR / "greenhouse" / "confirmation.html").read_text()
    page = MockPortalPage(url="https://boards.greenhouse.io/acme/jobs/123/confirmation", content=conf_html)

    status, conf_type, ref_code, warnings = await adapter.detect_confirmation(page)
    assert status == ConfirmationStatus.CONFIRMED
    assert ref_code == "GH-948271"
    assert "URL" in conf_type or "DOM" in conf_type


@pytest.mark.asyncio
async def test_lever_adapter_confirmation():
    adapter = LeverPortalAdapter()
    assert adapter.matches("https://jobs.lever.co/company/abc") is True

    conf_html = (FIXTURES_DIR / "lever" / "confirmation.html").read_text()
    page = MockPortalPage(url="https://jobs.lever.co/company/abc/thanks", content=conf_html)

    status, conf_type, ref_code, warnings = await adapter.detect_confirmation(page)
    assert status == ConfirmationStatus.CONFIRMED
    assert ref_code == "LEV-882194"


@pytest.mark.asyncio
async def test_ashby_adapter_confirmation():
    adapter = AshbyPortalAdapter()
    assert adapter.matches("https://jobs.ashbyhq.com/notion/123") is True

    conf_html = (FIXTURES_DIR / "ashby" / "confirmation.html").read_text()
    page = MockPortalPage(url="https://jobs.ashbyhq.com/notion/123/application/submitted", content=conf_html)

    status, conf_type, ref_code, warnings = await adapter.detect_confirmation(page)
    assert status == ConfirmationStatus.CONFIRMED
    assert ref_code == "ASH-551029"


@pytest.mark.asyncio
async def test_generic_adapter_ambiguous():
    adapter = GenericATSPortalAdapter()
    assert adapter.matches("https://unknown-ats.org") is True

    ambig_html = (FIXTURES_DIR / "generic" / "ambiguous_submission.html").read_text()
    page = MockPortalPage(url="https://unknown-ats.org/careers", content=ambig_html)

    status, conf_type, ref_code, warnings = await adapter.detect_confirmation(page)
    assert status == ConfirmationStatus.UNKNOWN
    assert conf_type == "UNCONFIRMED_STATE"
    assert len(warnings) > 0
