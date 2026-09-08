from app.schemas.connector import ConnectorCapabilities


def get_greenhouse_capabilities() -> ConnectorCapabilities:
    """
    Capabilities for Greenhouse ATS connector.
    Phase 5: Can discover and read job details via public endpoints.
    Application filling/submission is False until later phases.
    """
    return ConnectorCapabilities(
        can_discover_jobs=True,
        can_get_job_details=True,
        can_prepare_application=False,
        can_fill_application=False,
        can_upload_resume=False,
        can_answer_questions=False,
        can_submit_application=False,
        requires_browser=False,
        requires_login=False,
        supports_persistent_session=False,
        requires_user_action=False,
    )


def get_lever_capabilities() -> ConnectorCapabilities:
    """
    Capabilities for Lever ATS connector.
    Phase 5: Can discover and read job details via public endpoints.
    """
    return ConnectorCapabilities(
        can_discover_jobs=True,
        can_get_job_details=True,
        can_prepare_application=False,
        can_fill_application=False,
        can_upload_resume=False,
        can_answer_questions=False,
        can_submit_application=False,
        requires_browser=False,
        requires_login=False,
        supports_persistent_session=False,
        requires_user_action=False,
    )


def get_ashby_capabilities() -> ConnectorCapabilities:
    """
    Capabilities for Ashby ATS connector.
    Phase 5: Can discover and read job details via public API.
    """
    return ConnectorCapabilities(
        can_discover_jobs=True,
        can_get_job_details=True,
        can_prepare_application=False,
        can_fill_application=False,
        can_upload_resume=False,
        can_answer_questions=False,
        can_submit_application=False,
        requires_browser=False,
        requires_login=False,
        supports_persistent_session=False,
        requires_user_action=False,
    )


def get_generic_browser_capabilities() -> ConnectorCapabilities:
    """
    Capabilities for Generic Browser fallback connector.
    Phase 5: Requires browser session. Submission is False until Phase 7/8.
    """
    return ConnectorCapabilities(
        can_discover_jobs=True,
        can_get_job_details=True,
        can_prepare_application=False,
        can_fill_application=False,
        can_upload_resume=False,
        can_answer_questions=False,
        can_submit_application=False,
        requires_browser=True,
        requires_login=False,
        supports_persistent_session=True,
        requires_user_action=False,
    )
