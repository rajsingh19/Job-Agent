import logging
from typing import Dict, List, Optional
from app.config.settings import Settings, get_settings
from app.services.discovery.sources.base import JobSource
from app.services.discovery.sources.greenhouse import GreenhouseSource
from app.services.discovery.sources.lever import LeverSource
from app.services.discovery.sources.ashby import AshbySource
from app.services.discovery.sources.browser import GenericBrowserDiscovery

logger = logging.getLogger(__name__)


class JobSourceRegistry:
    """Registry managing available job discovery connectors."""

    def __init__(self):
        self._sources: Dict[str, JobSource] = {}

    def register(self, source: JobSource) -> None:
        self._sources[source.name.lower()] = source
        logger.info(f"Registered job source: {source.name} (type: {source.source_type.value})")

    def unregister(self, name: str) -> Optional[JobSource]:
        return self._sources.pop(name.lower(), None)

    def get_source(self, name: str) -> Optional[JobSource]:
        return self._sources.get(name.lower())

    def get_all_sources(self) -> List[JobSource]:
        return list(self._sources.values())

    def get_enabled_sources(self) -> List[JobSource]:
        return [s for s in self._sources.values() if s.is_enabled]


def get_default_registry(settings: Optional[Settings] = None) -> JobSourceRegistry:
    """Creates a pre-configured source registry with default sources."""
    app_settings = settings or get_settings()
    registry = JobSourceRegistry()

    # 1. Official API Sources
    registry.register(
        GreenhouseSource(
            company_slugs=app_settings.greenhouse_company_slugs,
            timeout_seconds=app_settings.job_discovery_timeout_seconds,
        )
    )
    registry.register(
        LeverSource(
            company_slugs=app_settings.lever_company_slugs,
            timeout_seconds=app_settings.job_discovery_timeout_seconds,
        )
    )

    # 2. Public ATS Sources
    registry.register(
        AshbySource(
            company_slugs=app_settings.ashby_company_slugs,
            timeout_seconds=app_settings.job_discovery_timeout_seconds,
        )
    )

    # 3. Generic Browser Source Framework
    registry.register(
        GenericBrowserDiscovery(
            timeout_seconds=app_settings.job_discovery_timeout_seconds,
        )
    )

    return registry
