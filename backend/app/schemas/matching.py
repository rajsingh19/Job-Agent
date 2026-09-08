from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HardFilterResult(BaseModel):
    """Result of hard constraint evaluation for a candidate and job."""
    passed: bool
    failed_constraints: List[str] = Field(default_factory=list)
    unknown_constraints: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class JobMatchResult(BaseModel):
    """
    Comprehensive structured output of candidate-job matching and scoring.
    """
    job_id: str
    candidate_id: str
    job_title: str
    company: str
    is_hard_match: bool
    match_score: float = Field(..., ge=0.0, le=100.0, description="Normalized match score from 0 to 100")
    hard_filter_result: HardFilterResult
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    keyword_score: float = Field(..., ge=0.0, le=100.0)
    semantic_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    role_score: float = Field(..., ge=0.0, le=100.0)
    experience_score: float = Field(..., ge=0.0, le=100.0)
    explanation: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence indicator from 0.0 to 1.0")
    low_confidence: bool = False
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=lambda: datetime.now())

    model_config = ConfigDict(from_attributes=True)


class MatchQuery(BaseModel):
    """Parameters for matching one or more jobs."""
    resume_id: Optional[str] = None
    min_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    hard_match_only: bool = False


class RankedJobsQuery(BaseModel):
    """Query parameters for retrieving ranked job matches."""
    resume_id: Optional[str] = None
    min_score: float = Field(0.0, ge=0.0, le=100.0)
    hard_match_only: bool = False
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class RankedJobsResponse(BaseModel):
    """Response containing ranked job match results for a candidate."""
    results: List[JobMatchResult]
    total_matched: int
    total_hard_matched: int
    average_score: float
    candidate_id: str
