from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.job import JobPosting
from app.schemas.connector import (
    ApplicationMethod,
    ApplicationRoute,
    ATSDetectionResult,
    ConnectorCapabilities,
    PlatformType,
)


class PlatformConnector(ABC):
    """
    Abstract base class for all platform and ATS connectors.
    Provides route generation, capability reporting, and platform metadata.
    Designed for seamless extension in future phases (drafting, filling, submission).
    """

    @property
    @abstractmethod
    def platform(self) -> PlatformType:
        """The canonical platform type this connector handles."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable connector name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of connector support and routing."""
        pass

    @property
    @abstractmethod
    def supported_methods(self) -> List[ApplicationMethod]:
        """List of supported application methods for this platform."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ConnectorCapabilities:
        """Matrix of capabilities supported by this connector."""
        pass

    @abstractmethod
    async def detect(self, job: JobPosting) -> bool:
        """Returns True if this connector handles the given job posting."""
        pass

    @abstractmethod
    async def get_application_route(
        self,
        job: JobPosting,
        detection_result: Optional[ATSDetectionResult] = None,
    ) -> ApplicationRoute:
        """
        Determines the application routing parameters and constraints for the job posting.
        """
        pass
