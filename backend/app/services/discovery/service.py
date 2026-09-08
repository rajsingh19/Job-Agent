import asyncio
import logging
import time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import Settings, get_settings
from app.schemas.job import (
    DiscoveryResult,
    JobPostingCreate,
    JobPostingResponse,
    JobSearchQuery,
    SourceError,
)
from app.services.discovery.deduplication import JobDeduplicator
from app.services.discovery.registry import JobSourceRegistry, get_default_registry
from app.services.discovery.repository import JobRepository
from app.services.discovery.sources.base import JobSource

logger = logging.getLogger(__name__)


class JobDiscoveryService:
    """
    Orchestrates concurrent multi-source job discovery, failure isolation,
    deduplication, and idempotent database persistence.
    """

    def __init__(
        self,
        registry: Optional[JobSourceRegistry] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.registry = registry or get_default_registry(self.settings)
        self.repository = JobRepository()

    async def _execute_source_with_retry(
        self,
        source: JobSource,
        query: JobSearchQuery,
        semaphore: asyncio.Semaphore,
    ) -> tuple[List[JobPostingCreate], Optional[SourceError]]:
        """Executes a single source under concurrency control with exponential backoff retry."""
        async with semaphore:
            max_retries = self.settings.job_discovery_max_retries
            last_error: Optional[Exception] = None

            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"Running job discovery for source '{source.name}' (attempt {attempt}/{max_retries})")
                    jobs = await source.search_jobs(query)
                    logger.info(f"Source '{source.name}' discovered {len(jobs)} jobs")
                    return jobs, None
                except Exception as e:
                    last_error = e
                    logger.warning(f"Error on source '{source.name}' (attempt {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

            # If all retries exhausted, record isolated source error
            error_report = SourceError(
                source=source.name,
                error_code="SOURCE_EXECUTION_FAILED",
                message=str(last_error) if last_error else "Unknown error",
            )
            return [], error_report

    async def discover_jobs(
        self,
        db: AsyncSession,
        query: JobSearchQuery,
    ) -> DiscoveryResult:
        """
        Executes discovery across enabled sources, isolates failures, deduplicates,
        persists unique postings, and returns unified DiscoveryResult.
        """
        start_time = time.perf_counter()

        # Select target sources
        all_sources = self.registry.get_enabled_sources()
        if query.sources:
            requested_names = set(s.lower() for s in query.sources)
            selected_sources = [s for s in all_sources if s.name.lower() in requested_names]
        else:
            selected_sources = all_sources

        if not selected_sources:
            return DiscoveryResult(
                jobs=[],
                total_found=0,
                total_unique=0,
                sources_attempted=0,
                sources_succeeded=0,
                source_errors=[],
                duration_ms=0.0,
            )

        semaphore = asyncio.Semaphore(self.settings.job_discovery_max_concurrency)

        # Run sources concurrently
        tasks = [
            self._execute_source_with_retry(source=src, query=query, semaphore=semaphore)
            for src in selected_sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        raw_postings: List[JobPostingCreate] = []
        source_errors: List[SourceError] = []
        sources_succeeded = 0

        for jobs, error in results:
            if error:
                source_errors.append(error)
            else:
                sources_succeeded += 1
                raw_postings.extend(jobs)

        total_found = len(raw_postings)

        # 2. Deduplication Layer
        unique_postings, duplicates_removed = JobDeduplicator.deduplicate_postings(raw_postings)
        total_unique = len(unique_postings)
        logger.info(f"Discovery found {total_found} raw jobs. Deduplicated to {total_unique} unique jobs.")

        # 3. Database Persistence Layer
        persisted_models, created_count, updated_count = await self.repository.upsert_jobs(
            db=db,
            postings=unique_postings,
        )
        logger.info(f"Persisted jobs: {created_count} created, {updated_count} updated.")

        # Convert to response schemas
        response_jobs = [JobPostingResponse.model_validate(job) for job in persisted_models]

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return DiscoveryResult(
            jobs=response_jobs,
            total_found=total_found,
            total_unique=total_unique,
            sources_attempted=len(selected_sources),
            sources_succeeded=sources_succeeded,
            source_errors=source_errors,
            duration_ms=round(duration_ms, 2),
        )
