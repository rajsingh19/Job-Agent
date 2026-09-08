from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.enums import ATSProvider, RemoteType
from app.models.job import JobPosting
from app.schemas.job import (
    DiscoveryResult,
    JobFilter,
    JobPostingResponse,
    JobSearchQuery,
)
from app.schemas.matching import (
    JobMatchResult,
    MatchQuery,
    RankedJobsQuery,
    RankedJobsResponse,
)
from app.services.discovery.repository import JobRepository
from app.services.discovery.service import JobDiscoveryService
from app.services.matching.service import JobMatchingService
from app.services.profile.service import CandidateProfileService

router = APIRouter()
discovery_service = JobDiscoveryService()
job_repo = JobRepository()
matching_service = JobMatchingService()
profile_service = CandidateProfileService()


@router.post(
    "/discover",
    response_model=DiscoveryResult,
    summary="Trigger multi-source job discovery and normalization",
)
async def discover_jobs(
    query: JobSearchQuery,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes explicit job discovery across configured API, ATS, and browser sources.
    Normalizes, deduplicates, and saves newly discovered jobs into the database.
    """
    return await discovery_service.discover_jobs(db=db, query=query)


@router.get(
    "",
    response_model=List[JobPostingResponse],
    summary="List and filter discovered jobs",
)
async def list_jobs(
    sources: Optional[List[str]] = Query(None),
    remote_type: Optional[RemoteType] = Query(None),
    min_stipend: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves paginated normalized jobs matching filter parameters."""
    filter_params = JobFilter(
        sources=sources,
        remote_type=remote_type,
        min_stipend=min_stipend,
        limit=limit,
        offset=offset,
    )
    jobs, total = await job_repo.get_jobs(db=db, filter_params=filter_params)
    return [JobPostingResponse.model_validate(job) for job in jobs]


@router.get(
    "/ranked",
    response_model=RankedJobsResponse,
    summary="Get all saved active jobs ranked against candidate profile",
)
async def get_ranked_jobs(
    resume_id: Optional[str] = Query(None),
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    hard_match_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates composite match scores for all active jobs against the authenticated
    user's candidate profile, returning sorted results.
    """
    # 1. Fetch CandidateProfile
    candidate_profile = await profile_service.get_candidate_profile(
        db=db,
        user_id=user_id,
        resume_id=resume_id,
    )

    # 2. Fetch all active jobs
    jobs_result = await db.execute(
        select(JobPosting).where(JobPosting.is_active.is_(True))
    )
    all_jobs = list(jobs_result.scalars().all())

    # 3. Compute matching and ranking
    ranked_results = await matching_service.match_jobs(
        candidate_profile=candidate_profile,
        jobs=all_jobs,
        min_score=min_score,
        hard_match_only=hard_match_only,
    )

    total_matched = len(ranked_results)
    total_hard_matched = sum(1 for r in ranked_results if r.is_hard_match)
    avg_score = (
        round(sum(r.match_score for r in ranked_results) / total_matched, 1)
        if total_matched > 0
        else 0.0
    )

    # Apply pagination
    paginated_results = ranked_results[offset : offset + limit]

    return RankedJobsResponse(
        results=paginated_results,
        total_matched=total_matched,
        total_hard_matched=total_hard_matched,
        average_score=avg_score,
        candidate_id=user_id,
    )


@router.post(
    "/match",
    response_model=List[JobMatchResult],
    summary="Match multiple active jobs against candidate profile",
)
async def match_multiple_jobs(
    match_query: MatchQuery,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Matches active jobs against candidate profile and returns ranked list."""
    candidate_profile = await profile_service.get_candidate_profile(
        db=db,
        user_id=user_id,
        resume_id=match_query.resume_id,
    )
    jobs_result = await db.execute(
        select(JobPosting).where(JobPosting.is_active.is_(True))
    )
    all_jobs = list(jobs_result.scalars().all())

    return await matching_service.match_jobs(
        candidate_profile=candidate_profile,
        jobs=all_jobs,
        min_score=match_query.min_score or 0.0,
        hard_match_only=match_query.hard_match_only,
    )


@router.post(
    "/{job_id}/match",
    response_model=JobMatchResult,
    summary="Match a specific job posting against candidate profile",
)
async def match_single_job(
    job_id: str,
    resume_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Evaluates hard constraints, keyword overlap, semantic similarity, and scoring for a single job."""
    job = await job_repo.get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "JOB_NOT_FOUND", "message": f"Job with ID '{job_id}' was not found."},
        )

    candidate_profile = await profile_service.get_candidate_profile(
        db=db,
        user_id=user_id,
        resume_id=resume_id,
    )

    return await matching_service.match_job(
        candidate_profile=candidate_profile,
        job=job,
    )


@router.get(
    "/{job_id}",
    response_model=JobPostingResponse,
    summary="Get job posting details by ID",
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a specific normalized job posting."""
    job = await job_repo.get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "JOB_NOT_FOUND", "message": f"Job with ID '{job_id}' was not found."},
        )
    return JobPostingResponse.model_validate(job)
