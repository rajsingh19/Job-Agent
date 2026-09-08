import pytest
from app.services.browser.exceptions import BrowserExecutionError
from app.services.browser.navigation import NavigationHelper


def test_navigation_url_validation_rejects_malicious_schemes():
    """Verifies that navigation strictly forbids non-http(s) schemes such as file://, javascript:, data:."""
    assert NavigationHelper.validate_url("https://boards.greenhouse.io/company/jobs/123") is True
    assert NavigationHelper.validate_url("http://localhost:8000/application") is True

    assert NavigationHelper.validate_url("file:///etc/passwd") is False
    assert NavigationHelper.validate_url("javascript:alert(1)") is False
    assert NavigationHelper.validate_url("data:text/html,<script>alert(1)</script>") is False
    assert NavigationHelper.validate_url("") is False


@pytest.mark.asyncio
async def test_navigate_to_url_raises_for_forbidden_scheme():
    """Verifies that navigate_to_url raises BrowserExecutionError for invalid schemes."""
    with pytest.raises(BrowserExecutionError):
        await NavigationHelper.navigate_to_url(page=None, url="file:///etc/shadow")
