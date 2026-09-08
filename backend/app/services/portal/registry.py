import logging
from typing import Dict, List, Optional
from app.services.portal.adapters.base import PortalAdapter
from app.services.portal.adapters.greenhouse import GreenhousePortalAdapter
from app.services.portal.adapters.lever import LeverPortalAdapter
from app.services.portal.adapters.ashby import AshbyPortalAdapter
from app.services.portal.adapters.generic_ats import GenericATSPortalAdapter
from app.services.portal.models import PortalCapabilities, PortalConfig

logger = logging.getLogger(__name__)


class PortalRegistry:
    """
    Central registry for discovering and obtaining portal-specific adapters.
    Maintains specific ATS adapters first and falls back to GenericATSPortalAdapter.
    """
    _instance: Optional["PortalRegistry"] = None

    def __init__(self):
        self._adapters: List[PortalAdapter] = []
        self._fallback_adapter: PortalAdapter = GenericATSPortalAdapter()
        self._register_default_adapters()

    @classmethod
    def get_instance(cls) -> "PortalRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_default_adapters(self) -> None:
        self.register(GreenhousePortalAdapter())
        self.register(LeverPortalAdapter())
        self.register(AshbyPortalAdapter())

    def register(self, adapter: PortalAdapter) -> None:
        """Registers a new portal adapter with precedence over fallback."""
        self._adapters.append(adapter)
        logger.debug("Registered portal adapter: %s", adapter.portal_id)

    def get_adapter_for_url(self, url: str) -> PortalAdapter:
        """
        Returns the most appropriate portal adapter matching the target URL.
        Falls back to GenericATSPortalAdapter if no specific adapter matches.
        """
        if url:
            for adapter in self._adapters:
                if adapter.matches(url):
                    return adapter

        return self._fallback_adapter

    def get_adapter(self, portal_id: str) -> Optional[PortalAdapter]:
        """
        Retrieves a portal adapter by canonical ID.
        """
        for adapter in self._adapters:
            if adapter.portal_id.lower() == portal_id.lower():
                return adapter
        if self._fallback_adapter.portal_id.lower() == portal_id.lower():
            return self._fallback_adapter
        return None

    def list_all_capabilities(self) -> Dict[str, PortalCapabilities]:
        """Returns the capability matrix for all registered portal adapters."""
        res: Dict[str, PortalCapabilities] = {}
        for adapter in self._adapters:
            res[adapter.portal_id] = adapter.capabilities()
        res[self._fallback_adapter.portal_id] = self._fallback_adapter.capabilities()
        return res

    def list_all_configs(self) -> Dict[str, PortalConfig]:
        """Returns the configuration for all registered portal adapters."""
        res: Dict[str, PortalConfig] = {}
        for adapter in self._adapters:
            res[adapter.portal_id] = adapter.get_config()
        res[self._fallback_adapter.portal_id] = self._fallback_adapter.get_config()
        return res
