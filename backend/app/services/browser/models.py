from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.services.browser.enums import (
    AuthStatus,
    BrowserSessionStatus,
    ChallengeType,
    ExecutionStepState,
    FieldActionType,
    FieldMatchStatus,
)


class BrowserField(BaseModel):
    """Normalized representation of a visible DOM form field."""
    field_id: str
    name: Optional[str] = None
    label: Optional[str] = None
    input_type: str = "text"  # text, email, tel, url, textarea, select, checkbox, radio, file
    placeholder: Optional[str] = None
    selector: str
    required: bool = False
    options: List[str] = Field(default_factory=list)
    visible: bool = True
    enabled: bool = True
    value: Optional[str] = None
    autocomplete: Optional[str] = None


class DiscoveredForm(BaseModel):
    """Normalized application form structure discovered on a page."""
    form_id: str
    action_url: Optional[str] = None
    fields: List[BrowserField] = Field(default_factory=list)
    step_index: int = 1
    total_steps: Optional[int] = None
    has_next_button: bool = False
    has_submit_button: bool = False
    detected_platform: Optional[str] = None


class FieldExecutionAction(BaseModel):
    """An individual planned action on a form field."""
    field_id: str
    selector: str
    action_type: FieldActionType
    value: Optional[str] = None
    value_source: Optional[str] = None
    match_status: FieldMatchStatus = FieldMatchStatus.UNKNOWN
    requires_user_input: bool = False
    user_input_reason: Optional[str] = None
    executed: bool = False
    execution_error: Optional[str] = None


class BrowserExecutionPlan(BaseModel):
    """Ordered execution plan generated prior to modifying the form."""
    application_id: str
    step_name: str = "Step 1"
    actions: List[FieldExecutionAction] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScreenshotMetadata(BaseModel):
    """Safe metadata for visual execution checkpoints."""
    id: str
    step: str
    url: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filename: str
    relative_path: str


class BrowserSessionInfo(BaseModel):
    """Safe user-facing view of a browser session. Cookies and storage state are NEVER exposed."""
    session_id: str
    user_id: str
    status: BrowserSessionStatus
    current_url: Optional[str] = None
    auth_status: AuthStatus = AuthStatus.UNKNOWN
    challenge_type: ChallengeType = ChallengeType.NONE
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class ExecutionStateSnapshot(BaseModel):
    """Complete inspectable execution state for an application."""
    application_id: str
    session_id: Optional[str] = None
    current_url: Optional[str] = None
    current_step: str = "initial"
    state: ExecutionStepState = ExecutionStepState.NOT_STARTED
    auth_status: AuthStatus = AuthStatus.UNKNOWN
    challenge_type: ChallengeType = ChallengeType.NONE
    user_action_required: bool = False
    user_action_reason: Optional[str] = None
    user_instructions: Optional[str] = None
    discovered_fields: List[BrowserField] = Field(default_factory=list)
    execution_plan: Optional[BrowserExecutionPlan] = None
    executed_actions_count: int = 0
    total_actions_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    screenshots: List[ScreenshotMetadata] = Field(default_factory=list)
    portal_diagnostics: Optional[Dict[str, Any]] = None
    step_info: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
