import logging
from typing import List, Optional
import httpx
from app.models.enums import ATSProvider, JobSourceType
from app.schemas.job import JobPostingCreate, JobSearchQuery
from app.services.discovery.deduplication import JobDeduplicator
from app.services.discovery.normalization import JobNormalizer
from app.services.discovery.sources.base import APISource

logger = logging.getLogger(__name__)


class LeverSource(APISource):
    """
    Official public job postings API connector for Lever.
    Queries https://api.lever.co/v0/postings/{company}?mode=json
    """

    def __init__(
        self,
        company_slugs: Optional[List[str]] = None,
        timeout_seconds: float = 20.0,
        is_enabled: bool = True,
    ):
        super().__init__(name="Lever", is_enabled=is_enabled)
        self.company_slugs = company_slugs or ["palantir", "netflix", "affirm"]
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api.lever.co/v0/postings"

    async def search_jobs(self, query: JobSearchQuery) -> List[JobPostingCreate]:
        if not self.is_enabled:
            return []

        target_companies = query.company_slugs or self.company_slugs
        discovered_jobs: List[JobPostingCreate] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for company_slug in target_companies:
                try:
                    url = f"{self.base_url}/{company_slug}?mode=json"
                    response = await client.get(url)

                    if response.status_code == 404:
                        logger.warning(f"Lever postings not found for company slug: '{company_slug}'")
                        continue
                    elif response.status_code != 200:
                        logger.warning(f"Lever API error {response.status_code} for '{company_slug}'")
                        continue

                    postings_data = response.json()
                    if not isinstance(postings_data, list):
                        continue

                    for item in postings_data:
                        raw_title = item.get("text", "")
                        categories = item.get("categories", {})
                        raw_loc = categories.get("location")
                        raw_desc = item.get("descriptionPlain") or item.get("description", "")
                        hosted_url = item.get("hostedUrl", "")
                        apply_url = item.get("applyUrl") or hosted_url
                        external_id = item.get("id")

                        # Normalization
                        title = JobNormalizer.normalize_title(raw_title)
                        company = JobNormalizer.normalize_company_name(company_slug.replace("-", " ").title())
                        location = JobNormalizer.normalize_location(raw_loc)
                        description = JobNormalizer.clean_html_description(raw_desc)
                        remote_type = JobNormalizer.detect_remote_type(title, location, description)
                        experience_level = JobNormalizer.detect_experience_level(title, description)
                        skills = JobNormalizer.extract_skills(title, description)

                        # Keyword filtering
                        if query.keywords:
                            combined_text = f"{title} {description} {' '.join(skills)}".lower()
                            if not any(kw.lower() in combined_text for kw in query.keywords):
                                continue

                        # Location filtering
                        if query.locations:
                            loc_text = (location or "").lower()
                            if not any(l.lower() in loc_text for l in query.locations) and remote_type.value != "REMOTE":
                                continue

                        # Remote type filtering
                        if query.remote_type and query.remote_type.value != "ANY":
                            if remote_type.value != query.remote_type.value and remote_type.value != "ANY":
                                continue

                        source_hash = JobDeduplicator.generate_source_hash(
                            source="LEVER",
                            external_id=external_id,
                            company=company,
                            title=title,
                            location=location,
                            apply_url=apply_url,
                        )

                        posting = JobPostingCreate(
                            source="LEVER",
                            source_type=JobSourceType.API,
                            external_id=external_id,
                            title=title,
                            company=company,
                            location=location,
                            remote_type=remote_type,
                            description=description or title,
                            skills=skills,
                            apply_url=apply_url,
                            source_url=hosted_url,
                            ats_provider=ATSProvider.LEVER,
                            experience_level=experience_level,
                            source_hash=source_hash,
                            raw_data={"categories": categories, "createdAt": item.get("createdAt")},
                        )
                        discovered_jobs.append(posting)

                        if len(discovered_jobs) >= query.limit:
                            break

                except httpx.TimeoutException:
                    logger.warning(f"Timeout querying Lever for company '{company_slug}'")
                except Exception as e:
                    logger.warning(f"Error querying Lever for '{company_slug}': {e}")

                if len(discovered_jobs) >= query.limit:
                    break

        return discovered_jobs
