import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.portal.diagnostics import PortalDiagnosticsCollector
from app.services.portal.models import FormStepInfo


def test_portal_diagnostics_sanitization():
    unsafe_url = "https://boards.greenhouse.io/acme/jobs/123?token=secret123&password=foo&code=bar"
    sanitized = PortalDiagnosticsCollector.sanitize_url(unsafe_url)
    assert "token" not in sanitized
    assert "secret123" not in sanitized
    assert "password" not in sanitized
    assert sanitized == "https://boards.greenhouse.io/acme/jobs/123"

    diag = PortalDiagnosticsCollector.collect_diagnostics(
        portal_id="greenhouse",
        portal_name="Greenhouse",
        current_url=unsafe_url,
        step_info=FormStepInfo(step_index=1, total_steps=2, has_next=True),
        navigation_history=[unsafe_url, "https://boards.greenhouse.io/acme/jobs/123/step2?session_token=xyz"],
    )

    assert diag.url_domain == "boards.greenhouse.io"
    assert diag.current_step.step_index == 1
    assert all("token" not in u for u in diag.navigation_history)
    assert all("password" not in u for u in diag.navigation_history)


@pytest.mark.asyncio
async def test_portals_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List all portals
        resp = await ac.get("/api/v1/portals")
        assert resp.status_code == 200
        data = resp.json()
        assert "greenhouse" in data
        assert "lever" in data
        assert "ashby" in data
        assert "generic_ats" in data
        assert data["greenhouse"]["supports_resume_upload"] is True

        # 2. Get specific portal details
        resp_gh = await ac.get("/api/v1/portals/greenhouse")
        assert resp_gh.status_code == 200
        gh_data = resp_gh.json()
        assert gh_data["portal_id"] == "greenhouse"
        assert gh_data["capabilities"]["supports_multi_step_forms"] is True
        assert len(gh_data["config"]["submit_selectors"]) > 0

        # 3. Non-existent portal returns 404
        resp_404 = await ac.get("/api/v1/portals/non_existent_ats")
        assert resp_404.status_code == 404
