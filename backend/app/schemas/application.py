from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ApplicationStatus, ConnectorType
from app.schemas.job import JobPostingResponse
from app.schemas.resume import ResumeResponse
from app.schemas.status_history import StatusHistoryResponse


class FormFieldValue(BaseModel):
    field_name: str
    field_type: str = "text"
    value: Any
    confidence: float = 1.0
    source_field: Optional[str] = None


class GeneratedAnswer(BaseModel):
    question_id: str
    question_text: str
    answer_text: str
    confidence_score: float = 1.0
    grounded_in_field: Optional[str] = None  # Specific candidate profile/project reference


class ReviewPackage(BaseModel):
    """
    Complete application package presented to the user for explicit review and approval before submission.
    """
    job_title: str
    company: str
    apply_url: str
    selected_resume_id: Optional[str] = None
    populated_fields: Dict[str, Any] = Field(default_factory=dict)
    generated_answers: List[GeneratedAnswer] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    screenshot_path: Optional[str] = None
    requires_user_action_reason: Optional[str] = None


class ApplicationBase(BaseModel):
    connector: ConnectorType = ConnectorType.GENERIC_BROWSER
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    match_score: Optional[float] = None
    generated_answers: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    review_package: Dict[str, Any] = Field(default_factory=dict)


class ApplicationCreate(ApplicationBase):
    user_id: str
    job_id: str
    resume_id: Optional[str] = None


class ApplicationUpdate(BaseModel):
    resume_id: Optional[str] = None
    connector: Optional[ConnectorType] = None
    match_score: Optional[float] = None
    generated_answers: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    review_package: Optional[Dict[str, Any]] = None
    submission_response: Optional[Dict[str, Any]] = None


class ApplicationTransitionRequest(BaseModel):
    to_status: ApplicationStatus
    reason: Optional[str] = None
    actor: str = "USER"
    event_metadata: Dict[str, Any] = Field(default_factory=dict)


class ApplicationResponse(ApplicationBase):
    id: str
    user_id: str
    job_id: str
    resume_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submission_response: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    # Optional nested details
    job: Optional[JobPostingResponse] = None
    resume: Optional[ResumeResponse] = None
    status_history: List[StatusHistoryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
