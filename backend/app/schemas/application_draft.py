from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.connector import ApplicationMethod, PlatformType
from app.schemas.job import JobPostingResponse
from app.schemas.resume import ResumeResponse


class FieldType(str, Enum):
    """Supported form field input types for ATS and career portals."""
    TEXT = "TEXT"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    DATE = "DATE"
    NUMBER = "NUMBER"
    TEXTAREA = "TEXTAREA"
    SELECT = "SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    BOOLEAN = "BOOLEAN"
    FILE = "FILE"
    UNKNOWN = "UNKNOWN"


class FieldSource(str, Enum):
    """Origin of a field or question answer, enforcing data lineage and truthfulness."""
    USER_INPUT = "USER_INPUT"
    USER_PREFERENCE = "USER_PREFERENCE"
    CANDIDATE_PROFILE = "CANDIDATE_PROFILE"
    RESUME = "RESUME"
    DERIVED = "DERIVED"
    AI_GENERATED = "AI_GENERATED"
    UNKNOWN = "UNKNOWN"


class QuestionCategory(str, Enum):
    """Categorization for custom application questions."""
    PERSONAL_FACT = "PERSONAL_FACT"
    EDUCATION = "EDUCATION"
    EXPERIENCE = "EXPERIENCE"
    SKILL = "SKILL"
    MOTIVATION = "MOTIVATION"
    ROLE_FIT = "ROLE_FIT"
    PROJECT = "PROJECT"
    BEHAVIORAL = "BEHAVIORAL"
    WORK_AUTHORIZATION = "WORK_AUTHORIZATION"
    SALARY = "SALARY"
    AVAILABILITY = "AVAILABILITY"
    OTHER = "OTHER"


class ApplicationField(BaseModel):
    """A standardized field in an application draft."""
    field_id: str
    label: str
    field_type: FieldType = FieldType.TEXT
    value: Optional[Any] = None
    source: FieldSource = FieldSource.UNKNOWN
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    required: bool = False
    editable: bool = True
    warning: Optional[str] = None


class DraftCustomQuestion(BaseModel):
    """A custom question asked on an application form with its proposed answer."""
    question_id: str
    question: str
    category: QuestionCategory = QuestionCategory.OTHER
    answer: Optional[str] = None
    source: FieldSource = FieldSource.UNKNOWN
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    required: bool = True
    requires_review: bool = True
    requires_user_input: bool = False
    warning: Optional[str] = None


class CandidateApplicationContext(BaseModel):
    """
    Normalized, truthful candidate facts compiled for application drafting.
    Guaranteed not to invent or hallucinate data.
    """
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    education: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    # Explicit preferences only
    work_authorization: Optional[str] = None
    sponsorship_required: Optional[bool] = None
    available_from: Optional[str] = None
    expected_salary: Optional[float] = None


class ApplicationDraft(BaseModel):
    """
    Complete application draft for human inspection and subsequent browser automation.
    Phase 6 DOES NOT submit applications.
    """
    id: str = Field(..., description="Application ID associated with this draft")
    user_id: str
    job_id: str
    resume_id: str
    platform: PlatformType
    application_method: ApplicationMethod
    fields: List[ApplicationField] = Field(default_factory=list)
    custom_questions: List[DraftCustomQuestion] = Field(default_factory=list)
    cover_letter: Optional[str] = None
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    ready_for_review: bool = False
    requires_user_input: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ApplicationDraftCreateRequest(BaseModel):
    """Parameters for generating an application draft."""
    resume_id: Optional[str] = None
    custom_questions: Optional[List[Dict[str, Any]]] = None
    include_cover_letter: bool = True


class ApplicationDraftValidationResponse(BaseModel):
    """Validation response report for an application draft."""
    application_id: str
    is_valid: bool
    ready_for_review: bool
    requires_user_input: bool
    missing_fields: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ApplicationReviewPackageResponse(BaseModel):
    """Complete review package presented to the user for explicit approval."""
    application_id: str
    user_id: str
    job: JobPostingResponse
    selected_resume: Optional[ResumeResponse] = None
    platform: PlatformType
    application_method: ApplicationMethod
    fields: List[ApplicationField] = Field(default_factory=list)
    custom_questions: List[DraftCustomQuestion] = Field(default_factory=list)
    cover_letter: Optional[str] = None
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    ready_for_review: bool = False
    requires_user_input: bool = False
    screenshots: List[str] = Field(default_factory=list)
    requires_user_action_reason: Optional[str] = None
