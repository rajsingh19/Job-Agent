import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.services.browser.enums import AuthStatus, ChallengeType, ExecutionStepState
from app.services.browser.models import (
    BrowserExecutionPlan,
    BrowserField,
    ExecutionStateSnapshot,
    ScreenshotMetadata,
)

logger = logging.getLogger(__name__)


class ApplicationExecutionStore:
    """
    Thread-safe in-memory store of active execution states indexed by application_id.
    """
    _instance: Optional["ApplicationExecutionStore"] = None

    def __init__(self):
        self._states: Dict[str, ExecutionStateSnapshot] = {}

    @classmethod
    def get_instance(cls) -> "ApplicationExecutionStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init_execution(self, application_id: str, session_id: str) -> ExecutionStateSnapshot:
        snapshot = ExecutionStateSnapshot(
            application_id=application_id,
            session_id=session_id,
            state=ExecutionStepState.STARTING_BROWSER,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._states[application_id] = snapshot
        return snapshot

    def get_snapshot(self, application_id: str) -> Optional[ExecutionStateSnapshot]:
        return self._states.get(application_id)

    def update_state(
        self,
        application_id: str,
        state: Optional[ExecutionStepState] = None,
        current_step: Optional[str] = None,
        current_url: Optional[str] = None,
        auth_status: Optional[AuthStatus] = None,
        challenge_type: Optional[ChallengeType] = None,
        user_action_required: Optional[bool] = None,
        user_action_reason: Optional[str] = None,
        user_instructions: Optional[str] = None,
        discovered_fields: Optional[List[BrowserField]] = None,
        execution_plan: Optional[BrowserExecutionPlan] = None,
        warning: Optional[str] = None,
        screenshot: Optional[ScreenshotMetadata] = None,
    ) -> ExecutionStateSnapshot:
        snapshot = self._states.get(application_id)
        if not snapshot:
            snapshot = ExecutionStateSnapshot(application_id=application_id)
            self._states[application_id] = snapshot

        if state is not None:
            snapshot.state = state
        if current_step is not None:
            snapshot.current_step = current_step
        if current_url is not None:
            snapshot.current_url = current_url
        if auth_status is not None:
            snapshot.auth_status = auth_status
        if challenge_type is not None:
            snapshot.challenge_type = challenge_type
        if user_action_required is not None:
            snapshot.user_action_required = user_action_required
        if user_action_reason is not None:
            snapshot.user_action_reason = user_action_reason
        if user_instructions is not None:
            snapshot.user_instructions = user_instructions
        if discovered_fields is not None:
            snapshot.discovered_fields = discovered_fields
        if execution_plan is not None:
            snapshot.execution_plan = execution_plan
            snapshot.total_actions_count = len(execution_plan.actions)
            snapshot.executed_actions_count = sum(1 for a in execution_plan.actions if a.executed)
        if warning:
            snapshot.warnings.append(warning)
        if screenshot:
            snapshot.screenshots.append(screenshot)

        snapshot.updated_at = datetime.now(timezone.utc)
        return snapshot
