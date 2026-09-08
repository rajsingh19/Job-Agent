import pytest
from app.services.browser.browser_manager import BrowserManager


@pytest.mark.asyncio
async def test_browser_manager_lifecycle():
    """Verifies that BrowserManager initializes, creates contexts, and shuts down safely."""
    bm = await BrowserManager.get_instance()
    assert bm is not None

    session_ctx = await bm.create_session(
        session_id="test_sess_001",
        user_id="user_test_001",
    )
    assert session_ctx is not None
    assert session_ctx.session_id == "test_sess_001"
    assert session_ctx.page is not None

    # Test that session is tracked
    retrieved = bm.get_session("test_sess_001")
    assert retrieved is session_ctx

    # Clean close
    await bm.close_session("test_sess_001")
    assert bm.get_session("test_sess_001") is None

    # Shutdown
    await bm.shutdown()
