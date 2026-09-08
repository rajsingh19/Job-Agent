from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """Supported ATS and job application platforms."""
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    LINKEDIN = "linkedin"
    INTERNSHALA = "internshala"
    NAUKRI = "naukri"
    SHINE = "shine"
    WELLFOUND = "wellfound"
    GENERIC_ATS = "generic_ats"
    BROWSER = "browser"
    UNKNOWN = "unknown"


class ApplicationMethod(str, Enum):
    """Determined mechanism allowed to submit or handle the application."""
    API = "api"
    ATS = "ats"
    BROWSER = "browser"
    EXTERNAL_REDIRECT = "external_redirect"
    USER_ACTION = "user_action"
    UNKNOWN = "unknown"


class ConnectorCapabilities(BaseModel):
    """
    Explicit capability matrix for a platform connector.
    Phase 5 connectors accurately declare capabilities and strictly report
    can_submit_application=False until Phase 8.
    """
    can_discover_jobs: bool = False
    can_get_job_details: bool = False
    can_prepare_application: bool = False
    can_fill_application: bool = False
    can_upload_resume: bool = False
    can_answer_questions: bool = False
    can_submit_application: bool = False
    requires_browser: bool = False
    requires_login: bool = False
    supports_persistent_session: bool = False
    requires_user_action: bool = False


class ATSDetectionResult(BaseModel):
    """Result of analyzing job metadata, URLs, and platform signals."""
    platform: PlatformType
    confidence: float = Field(..., ge=0.0, le=1.0, description="Quality indicator between 0.0 and 1.0")
    signals: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    requires_browser: bool = False


class ApplicationRoute(BaseModel):
    """Full routing decision for applying to a discovered job posting."""
    job_id: str
    platform: PlatformType
    connector: str
    application_method: ApplicationMethod
    capabilities: ConnectorCapabilities
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_browser: bool
    requires_login: bool
    requires_user_action: bool
    signals: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PlatformDetectResponse(BaseModel):
    """API response for platform detection."""
    job_id: str
    platform: PlatformType
    confidence: float = Field(..., ge=0.0, le=1.0)
    application_method: ApplicationMethod
    requires_browser: bool
    requires_user_action: bool
    signals: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ConnectorInfo(BaseModel):
    """Registered connector metadata and capability summary."""
    platform: PlatformType
    name: str
    capabilities: ConnectorCapabilities
    supported_methods: List[ApplicationMethod]
    description: str
