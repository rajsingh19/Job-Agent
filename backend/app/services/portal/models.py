from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PortalCapabilities(BaseModel):
    """
    Capability matrix describing verified operations supported for a specific job portal.
    Never claims support for features unless genuinely verified.
    """
    supports_multi_step_forms: bool = False
    supports_resume_upload: bool = True
    supports_cover_letter: bool = True
    supports_custom_questions: bool = True
    supports_select_fields: bool = True
    supports_checkbox_fields: bool = True
    supports_radio_fields: bool = True
    requires_login: bool = False
    supports_external_redirect: bool = False
    has_known_confirmation_patterns: bool = True


class FormStepInfo(BaseModel):
    """
    Metadata for multi-step application form progression.
    """
    step_index: int = 1
    total_steps: Optional[int] = None
    step_label: Optional[str] = None
    has_next: bool = False
    has_previous: bool = False
    has_submit: bool = False
    is_final_step: bool = False


class PortalErrorCategory(str, Enum):
    """
    Structured categories for portal automation errors.
    """
    AUTHENTICATION = "AUTHENTICATION"
    CHALLENGE = "CHALLENGE"
    NETWORK = "NETWORK"
    TIMEOUT = "TIMEOUT"
    FORM_CHANGED = "FORM_CHANGED"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    UPLOAD_FAILURE = "UPLOAD_FAILURE"
    NAVIGATION_FAILURE = "NAVIGATION_FAILURE"
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    PORTAL_UNSUPPORTED = "PORTAL_UNSUPPORTED"


class PortalExecutionError(Exception):
    """
    Structured exception describing a portal execution error with diagnostic attributes.
    """
    def __init__(
        self,
        category: PortalErrorCategory,
        code: str,
        message: str,
        recoverable: bool = False,
        requires_user_action: bool = False,
        retry_allowed: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.category = category
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.requires_user_action = requires_user_action
        self.retry_allowed = retry_allowed
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "requires_user_action": self.requires_user_action,
            "retry_allowed": self.retry_allowed,
            "details": self.details,
        }


class RetryPolicy(BaseModel):
    """
    Policy governing safe retries.
    STRICT INVARIANT: Never retries submissions, challenges, or authentication.
    """
    max_network_retries: int = 2
    network_backoff_base_seconds: float = 1.0
    allow_submit_retry: bool = False  # NEVER allowed to be True
    allow_challenge_retry: bool = False  # NEVER allowed to be True
    allow_auth_retry: bool = False  # NEVER allowed to be True

    @classmethod
    def is_action_retryable(cls, category: PortalErrorCategory) -> bool:
        """
        Determines whether an error category is safely retryable.
        """
        if category in (
            PortalErrorCategory.NETWORK,
            PortalErrorCategory.TIMEOUT,
            PortalErrorCategory.NAVIGATION_FAILURE,
        ):
            return True
        return False


class PortalDiagnostics(BaseModel):
    """
    Sanitized, safe diagnostics package for an application session.
    NEVER contains passwords, OTPs, session cookies, auth headers, or internal file paths.
    """
    portal_id: str
    portal_name: str
    url_domain: str
    current_step: FormStepInfo
    total_fields_discovered: int = 0
    missing_required_fields: List[str] = Field(default_factory=list)
    auth_state: str = "AUTHENTICATED"
    challenge_state: str = "NONE"
    selector_failures: List[str] = Field(default_factory=list)
    navigation_history: List[str] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortalConfig(BaseModel):
    """
    Declarative configuration for a specific ATS / job portal.
    """
    portal_id: str
    name: str
    domain_patterns: List[str] = Field(default_factory=list)
    url_patterns: List[str] = Field(default_factory=list)
    login_url_patterns: List[str] = Field(default_factory=list)
    form_selectors: List[str] = Field(default_factory=list)
    next_selectors: List[str] = Field(default_factory=list)
    submit_selectors: List[str] = Field(default_factory=list)
    resume_selectors: List[str] = Field(default_factory=list)
    confirmation_url_patterns: List[str] = Field(default_factory=list)
    confirmation_text_patterns: List[str] = Field(default_factory=list)
    confirmation_ref_patterns: List[str] = Field(default_factory=list)
    error_selectors: List[str] = Field(default_factory=list)
    challenge_selectors: List[str] = Field(default_factory=list)
    known_field_aliases: Dict[str, List[str]] = Field(default_factory=dict)
