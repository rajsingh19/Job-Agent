import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.browser.enums import BrowserSessionStatus, ExecutionStepState
from app.services.browser.execution_state import ApplicationExecutionStore


@pytest.mark.asyncio
async def test_browser_api_endpoints_integration():
    """
    Tests the REST API endpoints under /api/v1/browser:
    session creation, session retrieval, execution snapshot, pause, and screenshots.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a new browser session
        headers = {"X-User-ID": "test_api_user"}
        resp = await client.post("/api/v1/browser/sessions", headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert data["user_id"] == "test_api_user"
        assert data["status"] == BrowserSessionStatus.READY.value
        session_id = data["session_id"]

        # Ensure no secrets in response
        assert "cookies" not in data
        assert "storage_state" not in data

        # 2. Retrieve session metadata
        resp_get = await client.get(f"/api/v1/browser/sessions/{session_id}", headers=headers)
        assert resp_get.status_code == 200
        assert resp_get.json()["session_id"] == session_id

        # 3. Retrieve invalid session -> 404
        resp_404 = await client.get("/api/v1/browser/sessions/invalid_session_id", headers=headers)
        assert resp_404.status_code == 404

        # 4. Cross-user access rejected -> 404
        headers_other = {"X-User-ID": "other_user"}
        resp_forbidden = await client.get(f"/api/v1/browser/sessions/{session_id}", headers=headers_other)
        assert resp_forbidden.status_code == 404

        # 5. Initialize an execution snapshot in store and fetch via API
        store = ApplicationExecutionStore.get_instance()
        store.init_execution("app_test_int_1", session_id)
        store.update_state(
            application_id="app_test_int_1",
            state=ExecutionStepState.FORM_READY,
            current_step="inspecting",
        )

        resp_exec = await client.get("/api/v1/browser/applications/app_test_int_1/execution", headers=headers)
        assert resp_exec.status_code == 200
        exec_data = resp_exec.json()
        assert exec_data["application_id"] == "app_test_int_1"
        assert exec_data["state"] == ExecutionStepState.FORM_READY.value

        # 6. Pause execution
        resp_pause = await client.post(
            f"/api/v1/browser/sessions/{session_id}/pause",
            json={"application_id": "app_test_int_1"},
            headers=headers,
        )
        assert resp_pause.status_code == 200
        assert resp_pause.json()["state"] == ExecutionStepState.PAUSED_FOR_USER.value

        # 7. Get screenshots list
        resp_scr = await client.get("/api/v1/browser/applications/app_test_int_1/screenshots", headers=headers)
        assert resp_scr.status_code == 200
        assert isinstance(resp_scr.json(), list)
