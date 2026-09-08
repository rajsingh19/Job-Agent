import logging
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import httpx
from pydantic import BaseModel, Field
from app.models.enums import ATSProvider, JobSourceType
from app.schemas.job import JobPostingCreate, JobSearchQuery
from app.services.discovery.deduplication import JobDeduplicator
from app.services.discovery.normalization import JobNormalizer
from app.services.discovery.sources.base import BrowserSource
from app.services.exceptions import AppException

logger = logging.getLogger(__name__)


class BrowserDiscoveryConfig(BaseModel):
    """Configuration for generic browser/DOM-based job discovery."""
    source_name: str = "GenericBrowser"
    search_url_template: str = ""
    card_selector: str = ".job-card"
    title_selector: str = ".job-title"
    company_selector: str = ".company-name"
    location_selector: str = ".job-location"
    url_selector: str = "a"
    description_selector: Optional[str] = ".job-description"
    pagination_selector: Optional[str] = ".pagination-next"
    max_pages: int = 1
    default_company: str = "Unknown Company"
    headers: Dict[str, str] = Field(default_factory=lambda: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })


class GenericBrowserDiscovery(BrowserSource):
    """
    Browser & DOM-based job discovery connector.
    Parses structured HTML job cards from configured web portals while strictly respecting
    anti-bot protections and login requirements without bypassing them.
    """

    def __init__(
        self,
        config: Optional[BrowserDiscoveryConfig] = None,
        timeout_seconds: float = 20.0,
        is_enabled: bool = True,
    ):
        source_name = config.source_name if config else "GenericBrowser"
        super().__init__(name=source_name, is_enabled=is_enabled)
        self.config = config or BrowserDiscoveryConfig()
        self.timeout_seconds = timeout_seconds

    def parse_html_cards(self, html_content: str, base_url: str = "") -> List[JobPostingCreate]:
        """Parses job cards from raw HTML using BeautifulSoup selector hierarchy."""
        soup = BeautifulSoup(html_content, "html.parser")
        postings: List[JobPostingCreate] = []

        # Check for bot challenge or login walls
        lower_html = html_content.lower()
        if any(challenge in lower_html for challenge in ["recaptcha", "cf-turnstile", "security check", "verify you are human", "sign in to continue"]):
            logger.warning(f"Bot protection or login wall detected on {self.name}. Pausing.")
            return []

        cards = soup.select(self.config.card_selector)
        for card in cards:
            title_elem = card.select_one(self.config.title_selector)
            raw_title = title_elem.get_text(strip=True) if title_elem else ""
            if not raw_title:
                continue

            company_elem = card.select_one(self.config.company_selector)
            raw_company = company_elem.get_text(strip=True) if company_elem else self.config.default_company

            loc_elem = card.select_one(self.config.location_selector)
            raw_loc = loc_elem.get_text(strip=True) if loc_elem else None

            url_elem = card.select_one(self.config.url_selector)
            raw_url = url_elem.get("href", "") if url_elem else base_url
            if raw_url.startswith("/") and base_url:
                from urllib.parse import urljoin
                apply_url = urljoin(base_url, raw_url)
            else:
                apply_url = raw_url or base_url

            desc_elem = card.select_one(self.config.description_selector) if self.config.description_selector else None
            raw_desc = desc_elem.get_text(strip=True) if desc_elem else ""

            # Normalize
            title = JobNormalizer.normalize_title(raw_title)
            company = JobNormalizer.normalize_company_name(raw_company)
            location = JobNormalizer.normalize_location(raw_loc)
            description = JobNormalizer.clean_html_description(raw_desc)
            remote_type = JobNormalizer.detect_remote_type(title, location, description)
            experience_level = JobNormalizer.detect_experience_level(title, description)
            skills = JobNormalizer.extract_skills(title, description)

            source_hash = JobDeduplicator.generate_source_hash(
                source=self.name,
                external_id=None,
                company=company,
                title=title,
                location=location,
                apply_url=apply_url,
            )

            posting = JobPostingCreate(
                source=self.name,
                source_type=JobSourceType.BROWSER,
                title=title,
                company=company,
                location=location,
                remote_type=remote_type,
                description=description or title,
                skills=skills,
                apply_url=apply_url,
                source_url=apply_url,
                ats_provider=ATSProvider.UNKNOWN,
                experience_level=experience_level,
                source_hash=source_hash,
            )
            postings.append(posting)

        return postings

    async def search_jobs(self, query: JobSearchQuery) -> List[JobPostingCreate]:
        if not self.is_enabled or not self.config.search_url_template:
            return []

        # Formulate search URL
        keyword_str = "+".join(query.keywords) if query.keywords else "software"
        search_url = self.config.search_url_template.format(keywords=keyword_str)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=self.config.headers) as client:
                response = await client.get(search_url)
                if response.status_code != 200:
                    logger.warning(f"Browser discovery request failed with status {response.status_code}")
                    return []

                return self.parse_html_cards(response.text, base_url=search_url)

        except Exception as e:
            logger.warning(f"Browser discovery error on {self.name}: {e}")
            return []
