from typing import List, Optional
from app.models.job import JobPosting
from app.schemas.connector import (
    ApplicationMethod,
    ApplicationRoute,
    ATSDetectionResult,
    ConnectorCapabilities,
    PlatformType,
)
from app.services.connectors.base import PlatformConnector
from app.services.connectors.capabilities import get_lever_capabilities


class LeverConnector(PlatformConnector):
    """
    Connector for Lever ATS platform (jobs.lever.co).
    """

    @property
    def platform(self) -> PlatformType:
        return PlatformType.LEVER

    @property
    def name(self) -> str:
        return "Lever ATS Connector"

    @property
    def description(self) -> str:
        return "Native ATS connector for Lever job postings and application routing."

    @property
    def supported_methods(self) -> List[ApplicationMethod]:
        return [ApplicationMethod.ATS, ApplicationMethod.API]

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return get_lever_capabilities()

    async def detect(self, job: JobPosting) -> bool:
        url = (job.apply_url or "").lower()
        source = (job.source or "").lower()
        return "lever.co" in url or source == "lever"

    async def get_application_route(
        self,
        job: JobPosting,
        detection_result: Optional[ATSDetectionResult] = None,
    ) -> ApplicationRoute:
        confidence = detection_result.confidence if detection_result else 0.95
        signals = detection_result.signals if detection_result else ["connector=LeverConnector"]
        warnings = detection_result.warnings if detection_result else []

        return ApplicationRoute(
            job_id=str(job.id),
            platform=self.platform,
            connector=self.name,
            application_method=ApplicationMethod.ATS,
            capabilities=self.capabilities,
            confidence=confidence,
            requires_browser=False,
            requires_login=False,
            requires_user_action=False,
            signals=signals,
            warnings=warnings,
        )
