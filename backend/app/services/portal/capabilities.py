from typing import Dict
from app.services.portal.models import PortalCapabilities


def get_greenhouse_portal_capabilities() -> PortalCapabilities:
    """
    Capabilities for Greenhouse ATS portal:
    - Supports single-page and multi-step forms
    - Supports file upload for resumes and cover letters
    - Supports custom questions, dropdowns, and checkboxes
    - Rarely requires login for initial application
    - Well-defined confirmation URL and DOM banners
    """
    return PortalCapabilities(
        supports_multi_step_forms=True,
        supports_resume_upload=True,
        supports_cover_letter=True,
        supports_custom_questions=True,
        supports_select_fields=True,
        supports_checkbox_fields=True,
        supports_radio_fields=True,
        requires_login=False,
        supports_external_redirect=False,
        has_known_confirmation_patterns=True,
    )


def get_lever_portal_capabilities() -> PortalCapabilities:
    """
    Capabilities for Lever ATS portal:
    - Typically single-page applications with multi-section forms
    - Supports file upload for resumes
    - Supports custom questions, radio buttons, checkboxes, dropdowns
    - Does not require login for candidates
    - Redirects to confirmation page (/thanks) with identifiable DOM text
    """
    return PortalCapabilities(
        supports_multi_step_forms=False,
        supports_resume_upload=True,
        supports_cover_letter=True,
        supports_custom_questions=True,
        supports_select_fields=True,
        supports_checkbox_fields=True,
        supports_radio_fields=True,
        requires_login=False,
        supports_external_redirect=False,
        has_known_confirmation_patterns=True,
    )


def get_ashby_portal_capabilities() -> PortalCapabilities:
    """
    Capabilities for Ashby ATS portal:
    - Modern dynamic SPA with dynamic field loading
    - Supports multi-step / progressive disclosure forms
    - Supports custom questions and file uploads
    - Does not require login for standard applications
    - Reliable confirmation page and banner patterns
    """
    return PortalCapabilities(
        supports_multi_step_forms=True,
        supports_resume_upload=True,
        supports_cover_letter=True,
        supports_custom_questions=True,
        supports_select_fields=True,
        supports_checkbox_fields=True,
        supports_radio_fields=True,
        requires_login=False,
        supports_external_redirect=False,
        has_known_confirmation_patterns=True,
    )


def get_generic_ats_portal_capabilities() -> PortalCapabilities:
    """
    Conservative capabilities for unknown or generic ATS portals (Workday, BambooHR, iCIMS, etc.):
    - Conservative defaults; treats multi-step forms as possible
    - May require login (e.g. Workday accounts)
    - Fallback confirmation heuristics
    """
    return PortalCapabilities(
        supports_multi_step_forms=True,
        supports_resume_upload=True,
        supports_cover_letter=True,
        supports_custom_questions=True,
        supports_select_fields=True,
        supports_checkbox_fields=True,
        supports_radio_fields=True,
        requires_login=False,
        supports_external_redirect=True,
        has_known_confirmation_patterns=False,
    )


PORTAL_CAPABILITIES_MAP: Dict[str, PortalCapabilities] = {
    "greenhouse": get_greenhouse_portal_capabilities(),
    "lever": get_lever_portal_capabilities(),
    "ashby": get_ashby_portal_capabilities(),
    "generic_ats": get_generic_ats_portal_capabilities(),
}
