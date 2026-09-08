from datetime import datetime
import logging
from typing import List, Optional
import httpx
from app.models.enums import ATSProvider, JobSourceType
from app.schemas.job import JobPostingCreate, JobSearchQuery
from app.services.discovery.deduplication import JobDeduplicator
from app.services.discovery.normalization import JobNormalizer
from app.services.discovery.sources.base import APISource

logger = logging.getLogger(__name__)


class GreenhouseSource(APISource):
    """
    Official public job board API connector for Greenhouse.
    Queries https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
    """

    def __init__(
        self,
        company_slugs: Optional[List[str]] = None,
        timeout_seconds: float = 20.0,
        is_enabled: bool = True,
    ):
        super().__init__(name="Greenhouse", is_enabled=is_enabled)
        self.company_slugs = company_slugs or ["gitlab", "canonical", "cloudflare", "stripe"]
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://boards-api.greenhouse.io/v1/boards"

    async def search_jobs(self, query: JobSearchQuery) -> List[JobPostingCreate]:
        if not self.is_enabled:
            return []

        target_companies = query.company_slugs or self.company_slugs
        discovered_jobs: List[JobPostingCreate] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for company_slug in target_companies:
                try:
                    url = f"{self.base_url}/{company_slug}/jobs?content=true"
                    response = await client.get(url)

                    if response.status_code == 404:
                        logger.warning(f"Greenhouse board not found for company slug: '{company_slug}'")
                        continue
                    elif response.status_code != 200:
                        logger.warning(f"Greenhouse API error {response.status_code} for '{company_slug}'")
                        continue

                    data = response.json()
                    jobs_data = data.get("jobs", [])

                    for item in jobs_data:
                        raw_title = item.get("title", "")
                        raw_loc = item.get("location", {}).get("name")
                        raw_content = item.get("content", "")
                        apply_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{company_slug}/jobs/{item.get('id')}"
                        external_id = str(item.get("id"))

                        # Normalize fields
                        title = JobNormalizer.normalize_title(raw_title)
                        company = JobNormalizer.normalize_company_name(company_slug.replace("-", " ").title())
                        location = JobNormalizer.normalize_location(raw_loc)
                        description = JobNormalizer.clean_html_description(raw_content)
                        remote_type = JobNormalizer.detect_remote_type(title, location, description)
                        experience_level = JobNormalizer.detect_experience_level(title, description)
                        skills = JobNormalizer.extract_skills(title, description)

                        # Keyword filter matching if requested in query
                        if query.keywords:
                            combined_text = f"{title} {description} {' '.join(skills)}".lower()
                            if not any(kw.lower() in combined_text for kw in query.keywords):
                                continue

                        # Location filter matching if requested
                        if query.locations:
                            loc_text = (location or "").lower()
                            if not any(l.lower() in loc_text for l in query.locations) and remote_type.value != "REMOTE":
                                continue

                        # Remote filter matching if requested
                        if query.remote_type and query.remote_type.value != "ANY":
                            if remote_type.value != query.remote_type.value and remote_type.value != "ANY":
                                continue

                        # Generate deterministic source hash
                        source_hash = JobDeduplicator.generate_source_hash(
                            source="GREENHOUSE",
                            external_id=external_id,
                            company=company,
                            title=title,
                            location=location,
                            apply_url=apply_url,
                        )

                        posting = JobPostingCreate(
                            source="GREENHOUSE",
                            source_type=JobSourceType.API,
                            external_id=external_id,
                            title=title,
                            company=company,
                            location=location,
                            remote_type=remote_type,
                            description=description or title,
                            skills=skills,
                            apply_url=apply_url,
                            source_url=apply_url,
                            ats_provider=ATSProvider.GREENHOUSE,
                            experience_level=experience_level,
                            source_hash=source_hash,
                            raw_data={"departments": item.get("departments", []), "updated_at": item.get("updated_at")},
                        )
                        discovered_jobs.append(posting)

                        if len(discovered_jobs) >= query.limit:
                            break

                except httpx.TimeoutException:
                    logger.warning(f"Timeout querying Greenhouse for company '{company_slug}'")
                except Exception as e:
                    logger.warning(f"Error querying Greenhouse for '{company_slug}': {e}")

                if len(discovered_jobs) >= query.limit:
                    break

        return discovered_jobs
