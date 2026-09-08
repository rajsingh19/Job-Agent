import pytest
from app.services.browser.enums import BrowserSessionStatus
from app.services.browser.exceptions import BrowserSessionNotFoundError
from app.services.browser.session_manager import SessionManager


@pytest.mark.asyncio
async def test_session_manager_creation_and_ownership():
    """Verifies session creation, safe serialization, and tenant isolation."""
    sm = SessionManager.get_instance()

    info = await sm.create_session(user_id="user_alpha")
    assert info.session_id.startswith("bsess_")
    assert info.user_id == "user_alpha"
    assert info.status == BrowserSessionStatus.READY

    # Safe serialization: ensure no cookies/headers exposed
    dumped = info.model_dump()
    assert "cookies" not in dumped
    assert "storage_state" not in dumped

    # User alpha can retrieve their session
    record = sm.get_session_record(info.session_id, user_id="user_alpha")
    assert record.session_id == info.session_id

    # User beta CANNOT access user alpha's session
    with pytest.raises(BrowserSessionNotFoundError):
        sm.get_session_record(info.session_id, user_id="user_beta")

    # Clean close
    await sm.close_session(info.session_id, user_id="user_alpha")
    assert record.status == BrowserSessionStatus.COMPLETED
