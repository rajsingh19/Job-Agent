from app.services.portal.adapters.base import PortalAdapter
from app.services.portal.capabilities import get_greenhouse_portal_capabilities
from app.services.portal.config import get_greenhouse_config


class GreenhousePortalAdapter(PortalAdapter):
    """
    Dedicated compatibility adapter for Greenhouse ATS job boards.
    Handles boards.greenhouse.io multi-step forms, specialized file inputs,
    and standard confirmation structures.
    """

    def __init__(self):
        super().__init__(
            config=get_greenhouse_config(),
            capabilities=get_greenhouse_portal_capabilities(),
        )
