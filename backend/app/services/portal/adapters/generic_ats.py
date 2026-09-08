import logging
from typing import Any, Optional, Tuple
from app.services.portal.adapters.base import PortalAdapter
from app.services.portal.capabilities import get_generic_ats_portal_capabilities
from app.services.portal.config import get_generic_ats_config
from app.services.submission.models import ConfirmationStatus

logger = logging.getLogger(__name__)


class GenericATSPortalAdapter(PortalAdapter):
    """
    Robust, conservative fallback adapter for unknown ATS or custom application pages.
    Employs conservative heuristics: if confidence in final submission confirmation is ambiguous,
    safely returns UNKNOWN to prompt manual user verification.
    """

    def __init__(self):
        super().__init__(
            config=get_generic_ats_config(),
            capabilities=get_generic_ats_portal_capabilities(),
        )

    def matches(self, url: str) -> bool:
        """Fallback adapter matches any URL."""
        return True
