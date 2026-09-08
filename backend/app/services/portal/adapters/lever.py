from app.services.portal.adapters.base import PortalAdapter
from app.services.portal.capabilities import get_lever_portal_capabilities
from app.services.portal.config import get_lever_config


class LeverPortalAdapter(PortalAdapter):
    """
    Dedicated compatibility adapter for Lever ATS application pages.
    Handles jobs.lever.co single-page sections, custom questions, and redirect confirmations.
    """

    def __init__(self):
        super().__init__(
            config=get_lever_config(),
            capabilities=get_lever_portal_capabilities(),
        )
