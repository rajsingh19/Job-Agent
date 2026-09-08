from abc import ABC, abstractmethod
from typing import List
from app.models.enums import JobSourceType
from app.schemas.job import JobPostingCreate, JobSearchQuery


class JobSource(ABC):
    """Abstract base class for all job discovery sources."""

    def __init__(self, name: str, source_type: JobSourceType, is_enabled: bool = True):
        self.name = name
        self.source_type = source_type
        self.is_enabled = is_enabled

    @abstractmethod
    async def search_jobs(self, query: JobSearchQuery) -> List[JobPostingCreate]:
        """Discovers and returns normalized job postings matching the query."""
        pass


class APISource(JobSource, ABC):
    """Base class for official API-driven job sources."""

    def __init__(self, name: str, is_enabled: bool = True):
        super().__init__(name=name, source_type=JobSourceType.API, is_enabled=is_enabled)


class ATSSource(JobSource, ABC):
    """Base class for public ATS job board sources."""

    def __init__(self, name: str, is_enabled: bool = True):
        super().__init__(name=name, source_type=JobSourceType.ATS, is_enabled=is_enabled)


class BrowserSource(JobSource, ABC):
    """Base class for automated browser-based job discovery."""

    def __init__(self, name: str, is_enabled: bool = True):
        super().__init__(name=name, source_type=JobSourceType.BROWSER, is_enabled=is_enabled)
