import logging
from typing import List, Optional
from app.models.job import JobPosting
from app.schemas.connector import ApplicationRoute, ATSDetectionResult
from app.services.connectors.detector import ATSDetector
from app.services.connectors.registry import ConnectorRegistry, get_connector_registry

logger = logging.getLogger(__name__)


class ConnectorRouter:
    """
    Orchestrates ATS platform detection and connector resolution
    to produce deterministic ApplicationRoute decisions for job postings.
    """

    def __init__(
        self,
        detector: Optional[ATSDetector] = None,
        registry: Optional[ConnectorRegistry] = None,
    ):
        self.detector = detector or ATSDetector()
        self.registry = registry or get_connector_registry()

    async def route_job(self, job: JobPosting) -> ApplicationRoute:
        """
        Detects platform and determines application route and capabilities for a single job posting.
        """
        detection_result: ATSDetectionResult = self.detector.detect_platform(job)
        connector = self.registry.get_connector(detection_result.platform)

        if not connector:
            # Fallback to generic browser connector if no specialized connector found
            connector = self.registry.get_connector(detection_result.platform) or self.registry.get_connector(
                detection_result.platform
            )

        return await connector.get_application_route(job=job, detection_result=detection_result)

    async def route_jobs(self, jobs: List[JobPosting]) -> List[ApplicationRoute]:
        """Routes a batch of job postings."""
        routes: List[ApplicationRoute] = []
        for job in jobs:
            route = await self.route_job(job)
            routes.append(route)
        return routes


_default_router: Optional[ConnectorRouter] = None


def get_connector_router() -> ConnectorRouter:
    global _default_router
    if _default_router is None:
        _default_router = ConnectorRouter()
    return _default_router
