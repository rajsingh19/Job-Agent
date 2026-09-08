import logging
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import JobPosting
from app.schemas.job import JobFilter, JobPostingCreate

logger = logging.getLogger(__name__)


class JobRepository:
    """
    Handles idempotent persistence, retrieval, and filtering of JobPosting entities.
    """

    @staticmethod
    async def upsert_jobs(
        db: AsyncSession,
        postings: List[JobPostingCreate],
    ) -> Tuple[List[JobPosting], int, int]:
        """
        Idempotently inserts new job postings or updates existing ones matching on source_hash.
        Returns: (persisted_jobs, created_count, updated_count)
        """
        if not postings:
            return [], 0, 0

        persisted_jobs: List[JobPosting] = []
        created_count = 0
        updated_count = 0

        # Retrieve all existing jobs matching these source hashes in one query
        hashes = [p.source_hash for p in postings]
        result = await db.execute(select(JobPosting).where(JobPosting.source_hash.in_(hashes)))
        existing_map = {job.source_hash: job for job in result.scalars().all()}

        for item in postings:
            existing = existing_map.get(item.source_hash)
            if existing:
                # Update mutable attributes
                existing.title = item.title
                existing.location = item.location
                existing.remote_type = item.remote_type.value if hasattr(item.remote_type, "value") else str(item.remote_type)
                existing.description = item.description
                existing.skills = item.skills
                existing.apply_url = item.apply_url
                existing.is_active = item.is_active
                if item.experience_level:
                    existing.experience_level = item.experience_level.value if hasattr(item.experience_level, "value") else str(item.experience_level)
                persisted_jobs.append(existing)
                updated_count += 1
            else:
                new_job = JobPosting(
                    source=item.source,
                    source_type=item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type),
                    external_id=item.external_id,
                    title=item.title,
                    company=item.company,
                    location=item.location,
                    remote_type=item.remote_type.value if hasattr(item.remote_type, "value") else str(item.remote_type),
                    description=item.description,
                    skills=item.skills,
                    stipend_min=item.stipend_min,
                    stipend_max=item.stipend_max,
                    stipend_currency=item.stipend_currency,
                    salary_interval=item.salary_interval,
                    experience_level=item.experience_level.value if hasattr(item.experience_level, "value") else (str(item.experience_level) if item.experience_level else None),
                    apply_url=item.apply_url,
                    source_url=item.source_url,
                    ats_provider=item.ats_provider.value if hasattr(item.ats_provider, "value") else str(item.ats_provider),
                    source_hash=item.source_hash,
                    is_active=item.is_active,
                    raw_data=item.raw_data,
                )
                db.add(new_job)
                persisted_jobs.append(new_job)
                created_count += 1

        await db.commit()
        for job in persisted_jobs:
            await db.refresh(job)

        return persisted_jobs, created_count, updated_count

    @staticmethod
    async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[JobPosting]:
        result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_jobs(
        db: AsyncSession,
        filter_params: JobFilter,
    ) -> Tuple[List[JobPosting], int]:
        """Queries jobs with filtering and pagination."""
        query = select(JobPosting).where(JobPosting.is_active.is_(True))

        if filter_params.sources:
            query = query.where(JobPosting.source.in_(filter_params.sources))

        if filter_params.remote_type:
            remote_val = filter_params.remote_type.value if hasattr(filter_params.remote_type, "value") else str(filter_params.remote_type)
            if remote_val != "ANY":
                query = query.where(JobPosting.remote_type == remote_val)

        if filter_params.min_stipend is not None:
            query = query.where(JobPosting.stipend_min >= filter_params.min_stipend)

        # Count total matching
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await db.scalar(count_query) or 0

        # Apply ordering and pagination
        query = query.order_by(JobPosting.discovered_at.desc()).offset(filter_params.offset).limit(filter_params.limit)
        result = await db.execute(query)
        jobs = list(result.scalars().all())

        return jobs, total_count
