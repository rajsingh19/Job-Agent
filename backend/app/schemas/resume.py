from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EducationItem(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    company: str
    role: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    skills_used: List[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)


class CertificationItem(BaseModel):
    name: str
    issuer: str
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class ResumeProfile(BaseModel):
    """
    Structured candidate profile parsed from a resume.
    Separated from UserPreferences to prevent automatic LLM overwrites of user constraints.
    """
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    education: List[EducationItem] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    links: Dict[str, str] = Field(default_factory=dict)
    certifications: List[CertificationItem] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    low_confidence: bool = False
    raw_text: Optional[str] = None


class ResumeBase(BaseModel):
    name: str
    is_default: bool = False


class ResumeCreate(ResumeBase):
    user_id: str
    file_reference: str
    content_hash: str
    parsed_profile: ResumeProfile = Field(default_factory=ResumeProfile)


class ResumeResponse(ResumeBase):
    id: str
    user_id: str
    file_reference: str
    content_hash: str
    parsed_profile: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateProfile(BaseModel):
    """
    Combined candidate profile joining ResumeProfile and UserPreferences
    without mutating either source.
    """
    user_id: str
    resume_id: Optional[str] = None
    resume_profile: ResumeProfile
    preferences: Dict[str, Any]
    generated_at: datetime = Field(default_factory=lambda: datetime.now())
