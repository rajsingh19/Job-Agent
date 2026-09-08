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
