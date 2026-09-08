import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from app.config import get_settings
from app.services.browser.browser_manager import BrowserManager, BrowserSessionContext
from app.services.browser.enums import AuthStatus, BrowserSessionStatus, ChallengeType
from app.services.browser.exceptions import BrowserSessionNotFoundError
from app.services.browser.models import BrowserSessionInfo

logger = logging.getLogger(__name__)


class SessionRecord:
    """Internal tracking record for a browser session."""
    def __init__(
        self,
        session_id: str,
        user_id: str,
        status: BrowserSessionStatus = BrowserSessionStatus.CREATED,
        storage_state_path: Optional[str] = None,
    ):
        settings = get_settings()
        self.session_id = session_id
        self.user_id = user_id
        self.status = status
        self.current_url: Optional[str] = None
        self.auth_status: AuthStatus = AuthStatus.UNKNOWN
        self.challenge_type: ChallengeType = ChallengeType.NONE
        self.storage_state_path = storage_state_path
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.browser_session_timeout_minutes)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def touch(self) -> None:
        settings = get_settings()
        self.updated_at = datetime.now(timezone.utc)
        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.browser_session_timeout_minutes)

    def to_info(self) -> BrowserSessionInfo:
        """Converts to safe user-facing session info. Cookies/secrets are omitted."""
        return BrowserSessionInfo(
            session_id=self.session_id,
            user_id=self.user_id,
            status=self.status,
            current_url=self.current_url,
            auth_status=self.auth_status,
            challenge_type=self.challenge_type,
            created_at=self.created_at,
            updated_at=self.updated_at,
            expires_at=self.expires_at,
        )


class SessionManager:
    """
    Manages user browser sessions with strict tenant isolation and secure storage-state persistence.
    """
    _instance: Optional["SessionManager"] = None

    def __init__(self):
        self._sessions: Dict[str, SessionRecord] = {}

    @classmethod
    def get_instance(cls) -> "SessionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def create_session(self, user_id: str) -> BrowserSessionInfo:
        """
        Creates a new browser session for user_id with an isolated browser context.
        """
        settings = get_settings()
        session_id = f"bsess_{uuid.uuid4().hex[:12]}"

        # Storage state path for authenticated cookie preservation
        storage_filename = f"{user_id}_{session_id}_state.json"
        storage_path = (settings.browser_sessions_dir / storage_filename).resolve()

        record = SessionRecord(
            session_id=session_id,
            user_id=user_id,
            status=BrowserSessionStatus.CREATED,
            storage_state_path=str(storage_path) if storage_path.exists() else None,
        )
        self._sessions[session_id] = record

        # Initialize Playwright context
        bm = await BrowserManager.get_instance()
        await bm.create_session(
            session_id=session_id,
            user_id=user_id,
            storage_state_path=record.storage_state_path,
        )

        record.status = BrowserSessionStatus.READY
        logger.info("Session %s successfully created for user %s", session_id, user_id)
        return record.to_info()

    def get_session_record(self, session_id: str, user_id: str) -> SessionRecord:
        """
        Retrieves a session record ensuring strict user tenant ownership.
        """
        record = self._sessions.get(session_id)
        if not record:
            raise BrowserSessionNotFoundError(f"Browser session '{session_id}' not found.")

        if record.user_id != user_id:
            logger.warning("Access denied: User '%s' attempted to access session '%s' owned by '%s'", user_id, session_id, record.user_id)
            raise BrowserSessionNotFoundError(f"Browser session '{session_id}' not found.")

        if record.is_expired():
            record.status = BrowserSessionStatus.EXPIRED
            raise BrowserSessionNotFoundError(f"Browser session '{session_id}' has expired.")

        record.touch()
        return record

    async def save_storage_state(self, session_id: str, user_id: str) -> None:
        """
        Saves authenticated session cookies/state to storage_sessions securely with 0o600 permissions.
        """
        record = self.get_session_record(session_id, user_id)
        bm = await BrowserManager.get_instance()
        sess_ctx = bm.get_session(session_id)

        if sess_ctx and hasattr(sess_ctx.context, "storage_state"):
            settings = get_settings()
            storage_filename = f"{user_id}_{session_id}_state.json"
            storage_path = (settings.browser_sessions_dir / storage_filename).resolve()

            # Path traversal check
            if not str(storage_path).startswith(str(settings.browser_sessions_dir.resolve())):
                raise ValueError("Path traversal error in storage state path.")

            await sess_ctx.context.storage_state(path=str(storage_path))
            # Restrict permissions
            try:
                os.chmod(storage_path, 0o600)
            except Exception:
                pass
            record.storage_state_path = str(storage_path)
            logger.info("Persisted storage state for session %s with restricted permissions", session_id)

    async def close_session(self, session_id: str, user_id: str) -> None:
        """Closes browser session context and marks status as completed."""
        record = self.get_session_record(session_id, user_id)
        bm = await BrowserManager.get_instance()
        await bm.close_session(session_id)
        record.status = BrowserSessionStatus.COMPLETED
        logger.info("Closed and completed session %s for user %s", session_id, user_id)
