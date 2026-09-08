import pytest
from app.services.portal.capabilities import (
    get_ashby_portal_capabilities,
    get_generic_ats_portal_capabilities,
    get_greenhouse_portal_capabilities,
    get_lever_portal_capabilities,
)
from app.services.portal.models import PortalCapabilities, PortalConfig, RetryPolicy, PortalErrorCategory
from app.services.portal.registry import PortalRegistry


def test_portal_registry_resolution():
    registry = PortalRegistry.get_instance()

    # Greenhouse URLs
    gh_adapter = registry.get_adapter_for_url("https://boards.greenhouse.io/acme/jobs/12345")
    assert gh_adapter.portal_id == "greenhouse"
    assert gh_adapter.name == "Greenhouse"

    # Lever URLs
    lever_adapter = registry.get_adapter_for_url("https://jobs.lever.co/stripe/abc-123")
    assert lever_adapter.portal_id == "lever"
    assert lever_adapter.name == "Lever"

    # Ashby URLs
    ashby_adapter = registry.get_adapter_for_url("https://jobs.ashbyhq.com/notion/xyz-789")
    assert ashby_adapter.portal_id == "ashby"
    assert ashby_adapter.name == "Ashby"

    # Fallback Generic ATS URLs
    generic_adapter = registry.get_adapter_for_url("https://careers.randomcompany.com/apply")
    assert generic_adapter.portal_id == "generic_ats"
    assert generic_adapter.name == "Generic ATS"


def test_portal_capabilities_integrity():
    gh_caps = get_greenhouse_portal_capabilities()
    assert gh_caps.supports_multi_step_forms is True
    assert gh_caps.supports_resume_upload is True
    assert gh_caps.requires_login is False
    assert gh_caps.has_known_confirmation_patterns is True

    lever_caps = get_lever_portal_capabilities()
    assert lever_caps.supports_resume_upload is True
    assert lever_caps.requires_login is False

    ashby_caps = get_ashby_portal_capabilities()
    assert ashby_caps.supports_multi_step_forms is True
    assert ashby_caps.supports_resume_upload is True

    generic_caps = get_generic_ats_portal_capabilities()
    assert generic_caps.supports_external_redirect is True
    assert generic_caps.has_known_confirmation_patterns is False


def test_portal_registry_catalog():
    registry = PortalRegistry.get_instance()
    all_caps = registry.list_all_capabilities()
    assert "greenhouse" in all_caps
    assert "lever" in all_caps
    assert "ashby" in all_caps
    assert "generic_ats" in all_caps

    all_configs = registry.list_all_configs()
    assert "greenhouse" in all_configs
    assert "#submit_app" in all_configs["greenhouse"].submit_selectors


def test_retry_policy_invariants():
    # Safe retries allowed only for network/navigation/timeout
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.NETWORK) is True
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.TIMEOUT) is True
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.NAVIGATION_FAILURE) is True

    # Strictly disallowed retries
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.SUBMISSION_UNKNOWN) is False
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.AUTHENTICATION) is False
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.CHALLENGE) is False
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.UPLOAD_FAILURE) is False
