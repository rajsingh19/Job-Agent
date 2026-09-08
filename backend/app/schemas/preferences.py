from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import RemoteType, ExperienceLevel


class UserPreferencesBase(BaseModel):
    target_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_preference: RemoteType = Field(default=RemoteType.ANY)
    minimum_stipend: Optional[float] = None
    maximum_stipend: Optional[float] = None
    stipend_currency: str = "USD"
    experience_level: Optional[ExperienceLevel] = Field(default=ExperienceLevel.ENTRY_LEVEL)
    required_skills: List[str] = Field(default_factory=list)
    excluded_companies: List[str] = Field(default_factory=list)
    preferred_company_types: List[str] = Field(default_factory=list)
    additional_preferences: Dict[str, Any] = Field(default_factory=dict)


class UserPreferencesCreate(UserPreferencesBase):
    user_id: str


class UserPreferencesUpdate(BaseModel):
    target_roles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    remote_preference: Optional[RemoteType] = None
    minimum_stipend: Optional[float] = None
    maximum_stipend: Optional[float] = None
    stipend_currency: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None
    required_skills: Optional[List[str]] = None
    excluded_companies: Optional[List[str]] = None
    preferred_company_types: Optional[List[str]] = None
    additional_preferences: Optional[Dict[str, Any]] = None


class UserPreferencesResponse(UserPreferencesBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
