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
from app.services.connectors.capabilities import get_generic_browser_capabilities


class GenericBrowserConnector(PlatformConnector):
    """
    Fallback connector for job boards, company career portals, and platforms
    requiring automated browser sessions (e.g., LinkedIn, Internshala, Naukri, Shine, Wellfound).
    Never attempts to bypass CAPTCHA/OTP; routes to USER_ACTION when human interaction is required.
    """

    @property
    def platform(self) -> PlatformType:
        return PlatformType.BROWSER

    @property
    def name(self) -> str:
        return "Generic Browser Connector"

    @property
    def description(self) -> str:
        return "Browser automation fallback connector for non-API job boards and portal application flows."

    @property
    def supported_methods(self) -> List[ApplicationMethod]:
        return [ApplicationMethod.BROWSER, ApplicationMethod.USER_ACTION, ApplicationMethod.EXTERNAL_REDIRECT]

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return get_generic_browser_capabilities()

    async def detect(self, job: JobPosting) -> bool:
        # Fallback catches all job postings that reach it
        return True

    async def get_application_route(
        self,
        job: JobPosting,
        detection_result: Optional[ATSDetectionResult] = None,
    ) -> ApplicationRoute:
        platform = detection_result.platform if detection_result else PlatformType.BROWSER
        confidence = detection_result.confidence if detection_result else 0.80
        signals = detection_result.signals if detection_result else ["fallback=GenericBrowserConnector"]
        warnings = detection_result.warnings if detection_result else []

        # Determine if platform typically requires user action or login
        requires_login = platform in {
            PlatformType.LINKEDIN,
            PlatformType.INTERNSHALA,
            PlatformType.NAUKRI,
            PlatformType.SHINE,
            PlatformType.WELLFOUND,
        }

        # If platform is unknown and no reliable apply URL exists, route to USER_ACTION
        if platform == PlatformType.UNKNOWN or not job.apply_url:
            app_method = ApplicationMethod.USER_ACTION
            requires_user_action = True
            warnings.append("Job platform is unknown or unverified; human review required before application.")
        else:
            app_method = ApplicationMethod.BROWSER
            requires_user_action = False

        return ApplicationRoute(
            job_id=str(job.id),
            platform=platform,
            connector=self.name,
            application_method=app_method,
            capabilities=self.capabilities,
            confidence=confidence,
            requires_browser=True,
            requires_login=requires_login,
            requires_user_action=requires_user_action,
            signals=signals,
            warnings=warnings,
        )
