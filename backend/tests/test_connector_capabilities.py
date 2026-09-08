from app.services.connectors.ashby import AshbyConnector
from app.services.connectors.generic_browser import GenericBrowserConnector
from app.services.connectors.greenhouse import GreenhouseConnector
from app.services.connectors.lever import LeverConnector


def test_greenhouse_capabilities_honesty():
    connector = GreenhouseConnector()
    caps = connector.capabilities

    # Phase 5: Submission & filling are not yet implemented
    assert caps.can_submit_application is False
    assert caps.can_fill_application is False
    assert caps.can_prepare_application is False
    assert caps.can_upload_resume is False

    # Supported capabilities
    assert caps.can_discover_jobs is True
    assert caps.can_get_job_details is True
    assert caps.requires_browser is False


def test_lever_capabilities_honesty():
    connector = LeverConnector()
    caps = connector.capabilities

    assert caps.can_submit_application is False
    assert caps.can_fill_application is False
    assert caps.can_discover_jobs is True
    assert caps.can_get_job_details is True
    assert caps.requires_browser is False


def test_ashby_capabilities_honesty():
    connector = AshbyConnector()
    caps = connector.capabilities

    assert caps.can_submit_application is False
    assert caps.can_fill_application is False
    assert caps.can_discover_jobs is True
    assert caps.can_get_job_details is True
    assert caps.requires_browser is False


def test_generic_browser_capabilities_honesty():
    connector = GenericBrowserConnector()
    caps = connector.capabilities

    assert caps.can_submit_application is False
    assert caps.can_fill_application is False
    assert caps.can_discover_jobs is True
    assert caps.can_get_job_details is True
    assert caps.requires_browser is True
    assert caps.supports_persistent_session is True
