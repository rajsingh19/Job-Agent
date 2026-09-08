from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfirmationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    NOT_CONFIRMED = "NOT_CONFIRMED"
    UNKNOWN = "UNKNOWN"


class SubmissionAuthorization(BaseModel):
    """
    Cryptographically sealed authorization token passed to BrowserSubmitter.
    Binds the approval to the specific application, user, and content hash.
    """
    application_id: str
    user_id: str
    approved_version_hash: str
    approved_at: datetime
    token: str


class SubmissionResult(BaseModel):
    """Result of the final submission execution."""
    status: ConfirmationStatus
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmation_type: Optional[str] = None
    confirmation_reference: Optional[str] = None
    confirmation_url: Optional[str] = None
    screenshot_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class ApproveRequest(BaseModel):
    """Request body for human approval."""
    confirmation_checked: bool = Field(
        ...,
        description="Explicit user confirmation that the application was reviewed."
    )
    user_notes: Optional[str] = None


class SubmitRequest(BaseModel):
    """Request body for application submission."""
    approval_token: Optional[str] = None


class RevokeApprovalRequest(BaseModel):
    """Request body for revoking an approval."""
    reason: str = "User requested revision"


class ApprovalResponse(BaseModel):
    """Safe public response representing application approval status."""
    application_id: str
    status: str
    approved: bool
    approved_at: Optional[datetime] = None
    approved_version_hash: str
    approval_token: str
    ready_for_submission: bool


class SubmissionResponse(BaseModel):
    """Safe public response representing final submission outcome."""
    application_id: str
    status: str
    submitted_at: datetime
    confirmation_type: Optional[str] = None
    confirmation_reference: Optional[str] = None
    confirmation_url: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class AuditEventResponse(BaseModel):
    """Response model for immutable audit trail events."""
    id: str
    application_id: str
    event_type: str
    version_hash: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
