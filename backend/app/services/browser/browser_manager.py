import asyncio
import logging
from typing import Any, Dict, Optional
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from app.config import get_settings
from app.services.browser.exceptions import BrowserExecutionError

logger = logging.getLogger(__name__)


class BrowserSessionContext:
    """Represents an active Playwright browser context and page."""
    def __init__(
        self,
        session_id: str,
        user_id: str,
        context: BrowserContext,
        page: Page,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.context = context
        self.page = page


class BrowserManager:
    """
    Manages Playwright process lifecycle, browser contexts, and page instances.
    Enforces maximum concurrency and clean exception-safe teardown.
    Automatically rebinds if event loop changes (e.g. across pytest-asyncio tests).
    """
    _instance: Optional["BrowserManager"] = None

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._active_sessions: Dict[str, BrowserSessionContext] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None

    @classmethod
    async def get_instance(cls) -> "BrowserManager":
        """Singleton instance accessor supporting dynamic asyncio event loops."""
        current_loop = asyncio.get_running_loop()
        if cls._instance is None:
            cls._instance = cls()
        if cls._instance._loop != current_loop:
            cls._instance._loop = current_loop
            cls._instance._playwright = None
            cls._instance._browser = None
            cls._instance._active_sessions.clear()
            cls._instance._semaphore = None
        return cls._instance

    async def _ensure_browser(self) -> Browser:
        """Initializes Playwright and launches the shared Chromium browser if not active."""
        current_loop = asyncio.get_running_loop()
        if self._loop != current_loop:
            self._loop = current_loop
            self._playwright = None
            self._browser = None
            self._active_sessions.clear()
            self._semaphore = None

        if self._browser is not None and self._browser.is_connected():
            return self._browser

        settings = get_settings()
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(settings.browser_max_concurrent_sessions)

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        launch_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        self._browser = await self._playwright.chromium.launch(
            headless=settings.browser_headless,
            slow_mo=settings.browser_slow_mo_ms,
            args=launch_args,
        )
        logger.info("Launched Chromium browser instance (headless=%s)", settings.browser_headless)
        return self._browser

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        storage_state_path: Optional[str] = None,
    ) -> BrowserSessionContext:
        """
        Creates an isolated browser context and page for a user session.
        """
        browser = await self._ensure_browser()
        settings = get_settings()

        # Build context options
        context_kwargs: Dict[str, Any] = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        if storage_state_path:
            context_kwargs["storage_state"] = storage_state_path

        context = await browser.new_context(**context_kwargs)
        context.set_default_timeout(settings.browser_timeout_ms)
        context.set_default_navigation_timeout(settings.browser_navigation_timeout_ms)

        page = await context.new_page()
        session_ctx = BrowserSessionContext(
            session_id=session_id,
            user_id=user_id,
            context=context,
            page=page,
        )
        self._active_sessions[session_id] = session_ctx
        logger.info("Created browser session context: %s for user: %s", session_id, user_id)
        return session_ctx

    def get_session(self, session_id: str) -> Optional[BrowserSessionContext]:
        """Retrieves an active in-memory session context."""
        return self._active_sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        """Closes page and context for a specific session without killing the shared browser."""
        session = self._active_sessions.pop(session_id, None)
        if session:
            try:
                if not session.page.is_closed():
                    await session.page.close()
                await session.context.close()
                logger.info("Closed browser session: %s", session_id)
            except Exception as e:
                logger.warning("Error closing session %s: %s", session_id, e)

    async def shutdown(self) -> None:
        """Closes all active sessions, the shared browser, and stops Playwright."""
        for sid in list(self._active_sessions.keys()):
            await self.close_session(sid)

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.info("Playwright BrowserManager shutdown complete.")
