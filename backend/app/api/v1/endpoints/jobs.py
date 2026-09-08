from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.enums import ATSProvider, RemoteType
from app.schemas.job import (
    DiscoveryResult,
    JobFilter,
    JobPostingResponse,
    JobSearchQuery,
)
from app.services.discovery.repository import JobRepository
from app.services.discovery.service import JobDiscoveryService

router = APIRouter()
discovery_service = JobDiscoveryService()
job_repo = JobRepository()


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
