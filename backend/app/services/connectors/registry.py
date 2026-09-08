import logging
from typing import Dict, List, Optional
from app.schemas.connector import ConnectorInfo, PlatformType
from app.services.connectors.ashby import AshbyConnector
from app.services.connectors.base import PlatformConnector
from app.services.connectors.generic_browser import GenericBrowserConnector
from app.services.connectors.greenhouse import GreenhouseConnector
from app.services.connectors.lever import LeverConnector

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Central registry for platform connectors.
    Maintains connector lifecycle, handles registration validation,
    and prevents duplicate platform definitions.
    """

    def __init__(self):
        self._connectors: Dict[PlatformType, PlatformConnector] = {}

    def register(self, connector: PlatformConnector) -> None:
        """Registers a connector for its platform type. Raises ValueError on duplicate."""
        if not isinstance(connector, PlatformConnector):
            raise TypeError(f"Expected PlatformConnector instance, got {type(connector)}")

        platform = connector.platform
        if platform in self._connectors:
            raise ValueError(f"Connector for platform '{platform.value}' is already registered.")

        self._connectors[platform] = connector
        logger.info(f"Registered platform connector '{connector.name}' for '{platform.value}'")

    def unregister(self, platform: PlatformType) -> Optional[PlatformConnector]:
        """Unregisters a connector by platform type."""
        return self._connectors.pop(platform, None)

    def get_connector(self, platform: PlatformType) -> Optional[PlatformConnector]:
        """
        Retrieves the connector registered for the platform.
        Falls back to GenericBrowserConnector if platform is BROWSER, UNKNOWN, or a known browser portal.
        """
        if platform in self._connectors:
            return self._connectors[platform]

        # Check for generic browser connector fallback
        return self._connectors.get(PlatformType.BROWSER)

    def list_connectors(self) -> List[PlatformConnector]:
        """Returns all registered connectors."""
        return list(self._connectors.values())

    def list_connector_infos(self) -> List[ConnectorInfo]:
        """Returns metadata summary of registered connectors."""
        return [
            ConnectorInfo(
                platform=c.platform,
                name=c.name,
                capabilities=c.capabilities,
                supported_methods=c.supported_methods,
                description=c.description,
            )
            for c in self._connectors.values()
        ]

    def clear(self) -> None:
        """Clears all registered connectors."""
        self._connectors.clear()


# Default singleton registry pre-populated with standard Phase 5 connectors
_default_registry: Optional[ConnectorRegistry] = None


def get_connector_registry() -> ConnectorRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ConnectorRegistry()
        _default_registry.register(GreenhouseConnector())
        _default_registry.register(LeverConnector())
        _default_registry.register(AshbyConnector())
        _default_registry.register(GenericBrowserConnector())
    return _default_registry
