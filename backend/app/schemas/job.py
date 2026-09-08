from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ATSProvider, JobSourceType, RemoteType, ExperienceLevel


class JobPostingBase(BaseModel):
    source: str
    source_type: JobSourceType = JobSourceType.API
    external_id: Optional[str] = None
    title: str
    company: str
    location: Optional[str] = None
    remote_type: RemoteType = RemoteType.ANY
    description: str
    skills: List[str] = Field(default_factory=list)
    stipend_min: Optional[float] = None
    stipend_max: Optional[float] = None
    stipend_currency: str = "USD"
    salary_interval: Optional[str] = "month"
    experience_level: Optional[ExperienceLevel] = None
    apply_url: str
    source_url: Optional[str] = None
    ats_provider: ATSProvider = ATSProvider.UNKNOWN
    posted_at: Optional[datetime] = None
    is_active: bool = True
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class JobPostingCreate(JobPostingBase):
    source_hash: str


class JobPostingResponse(JobPostingBase):
    id: str
    source_hash: str
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobFilter(BaseModel):
    roles: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    remote_type: Optional[RemoteType] = None
    min_stipend: Optional[float] = None
    ats_providers: Optional[List[ATSProvider]] = None
    sources: Optional[List[str]] = None
    limit: int = 50
    offset: int = 0


class JobSearchQuery(BaseModel):
    """
    Search request parameters for the multi-source job discovery engine.
    """
    keywords: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    remote_type: Optional[RemoteType] = None
    experience_level: Optional[ExperienceLevel] = None
    limit: int = 50
    sources: Optional[List[str]] = None
    company_slugs: Optional[List[str]] = None


class SourceError(BaseModel):
    """Structured error report for a specific job source during discovery."""
    source: str
    error_code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class DiscoveryResult(BaseModel):
    """Unified result of a multi-source job discovery operation."""
    jobs: List[JobPostingResponse]
    total_found: int
    total_unique: int
    sources_attempted: int
    sources_succeeded: int
    source_errors: List[SourceError] = Field(default_factory=list)
    duration_ms: float = 0.0
