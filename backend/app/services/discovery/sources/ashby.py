import logging
from typing import List, Optional
import httpx
from app.models.enums import ATSProvider, JobSourceType, RemoteType
from app.schemas.job import JobPostingCreate, JobSearchQuery
from app.services.discovery.deduplication import JobDeduplicator
from app.services.discovery.normalization import JobNormalizer
from app.services.discovery.sources.base import ATSSource

logger = logging.getLogger(__name__)


class AshbySource(ATSSource):
    """
    Public ATS job board connector for Ashby.
    Queries https://api.ashbyhq.com/posting-api/job-board/{company}
    """

    def __init__(
        self,
        company_slugs: Optional[List[str]] = None,
        timeout_seconds: float = 20.0,
        is_enabled: bool = True,
    ):
        super().__init__(name="Ashby", is_enabled=is_enabled)
        self.company_slugs = company_slugs or ["ramp", "openai", "cursor"]
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api.ashbyhq.com/posting-api/job-board"

    async def search_jobs(self, query: JobSearchQuery) -> List[JobPostingCreate]:
        if not self.is_enabled:
            return []

        target_companies = query.company_slugs or self.company_slugs
        discovered_jobs: List[JobPostingCreate] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for company_slug in target_companies:
                try:
                    url = f"{self.base_url}/{company_slug}"
                    response = await client.get(url)

                    if response.status_code == 404:
                        logger.warning(f"Ashby board not found for company: '{company_slug}'")
                        continue
                    elif response.status_code != 200:
                        logger.warning(f"Ashby API returned status {response.status_code} for '{company_slug}'")
                        continue

                    data = response.json()
                    jobs_list = data.get("jobs", [])

                    for item in jobs_list:
                        raw_title = item.get("title", "")
                        raw_loc = item.get("location")
                        raw_desc = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
                        job_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{company_slug}/{item.get('id')}"
                        apply_url = item.get("applyUrl") or job_url
                        external_id = item.get("id")
                        is_remote = item.get("isRemote", False)

                        # Normalization
                        title = JobNormalizer.normalize_title(raw_title)
                        company = JobNormalizer.normalize_company_name(company_slug.replace("-", " ").title())
                        location = JobNormalizer.normalize_location(raw_loc)
                        description = JobNormalizer.clean_html_description(raw_desc)
                        remote_type = RemoteType.REMOTE if is_remote else JobNormalizer.detect_remote_type(title, location, description)
                        experience_level = JobNormalizer.detect_experience_level(title, description)
                        skills = JobNormalizer.extract_skills(title, description)

                        # Query Filters
                        if query.keywords:
                            combined = f"{title} {description} {' '.join(skills)}".lower()
                            if not any(kw.lower() in combined for kw in query.keywords):
                                continue

                        if query.locations and not is_remote:
                            loc_str = (location or "").lower()
                            if not any(l.lower() in loc_str for l in query.locations):
                                continue

                        if query.remote_type and query.remote_type.value != "ANY":
                            if remote_type.value != query.remote_type.value:
                                continue

                        source_hash = JobDeduplicator.generate_source_hash(
                            source="ASHBY",
                            external_id=external_id,
                            company=company,
                            title=title,
                            location=location,
                            apply_url=apply_url,
                        )

                        posting = JobPostingCreate(
                            source="ASHBY",
                            source_type=JobSourceType.ATS,
                            external_id=external_id,
                            title=title,
                            company=company,
                            location=location,
                            remote_type=remote_type,
                            description=description or title,
                            skills=skills,
                            apply_url=apply_url,
                            source_url=job_url,
                            ats_provider=ATSProvider.ASHBY,
                            experience_level=experience_level,
                            source_hash=source_hash,
                            raw_data={"publishedAt": item.get("publishedAt"), "department": item.get("department")},
                        )
                        discovered_jobs.append(posting)

                        if len(discovered_jobs) >= query.limit:
                            break

                except httpx.TimeoutException:
                    logger.warning(f"Timeout querying Ashby for '{company_slug}'")
                except Exception as e:
                    logger.warning(f"Error querying Ashby for '{company_slug}': {e}")

                if len(discovered_jobs) >= query.limit:
                    break

        return discovered_jobs
