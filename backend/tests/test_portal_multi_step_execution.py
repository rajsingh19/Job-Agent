import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.job import JobPosting
from app.services.browser.enums import ExecutionStepState
from app.services.browser.execution_service import BrowserExecutionService
from app.services.browser.models import BrowserField, DiscoveredForm, ExecutionStateSnapshot


class MockStepLocator:
    def __init__(self, visible=True):
        self._visible = visible

    async def count(self):
        return 1 if self._visible else 0

    @property
    def first(self):
        return self

    async def is_visible(self):
        return self._visible

    async def click(self, timeout=None):
        pass


class MockStepPage:
    def __init__(self):
        self.url = "https://boards.greenhouse.io/acme/jobs/123/step1"
        self._step = 1

    async def content(self):
        return f"Step {self._step} of 2"

    async def goto(self, url, timeout=None, wait_until=None):
        self.url = url

    def locator(self, selector: str):
        return MockStepLocator()

    async def wait_for_load_state(self, state, timeout=None):
        pass


@pytest.mark.asyncio
async def test_multi_step_navigation_helper():
    from app.services.browser.navigation import NavigationHelper
    page = MockStepPage()

    # validate_url guards
    assert NavigationHelper.validate_url("https://boards.greenhouse.io") is True
    assert NavigationHelper.validate_url("http://example.com") is True
    assert NavigationHelper.validate_url("javascript:alert(1)") is False
    assert NavigationHelper.validate_url("file:///etc/passwd") is False

    # wait_for_page_stability does not crash
    await NavigationHelper.wait_for_page_stability(page)
