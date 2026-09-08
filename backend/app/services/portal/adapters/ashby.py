from app.services.portal.adapters.base import PortalAdapter
from app.services.portal.capabilities import get_ashby_portal_capabilities
from app.services.portal.config import get_ashby_config


class AshbyPortalAdapter(PortalAdapter):
    """
    Dedicated compatibility adapter for Ashby ATS application forms.
    Handles modern dynamic React inputs, multi-step sections, and confirmation pages.
    """

    def __init__(self):
        super().__init__(
            config=get_ashby_config(),
            capabilities=get_ashby_portal_capabilities(),
        )
