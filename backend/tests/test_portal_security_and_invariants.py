import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.browser.exceptions import SubmissionBlockedError
from app.services.portal.models import PortalErrorCategory, RetryPolicy
from app.services.submission.browser_submitter import BrowserSubmitter
from app.services.submission.confirmation import SubmissionConfirmationDetector
from app.services.submission.exceptions import SubmissionBlockedError as SubBlockedError
from app.services.submission.models import ConfirmationStatus, SubmissionAuthorization


@pytest.mark.asyncio
async def test_portal_layer_preserves_no_approval_no_submission_invariant():
    page = MagicMock()
    page.url = "https://boards.greenhouse.io/acme/jobs/123"

    # 1. Attempting submission without authorization must raise SubBlockedError
    with pytest.raises(SubBlockedError):
        await BrowserSubmitter.submit(
            page=page,
            authorization=None,
            application_id="app_123",
        )

    # 2. Attempting submission with authorization belonging to another application
    from datetime import datetime, timezone
    auth_mismatch = SubmissionAuthorization(
        token="token_xyz",
        application_id="app_DIFFERENT",
        user_id="user_123",
        approved_version_hash="hash_abc",
        approved_at=datetime.now(timezone.utc),
    )
    with pytest.raises(SubBlockedError) as excinfo:
        await BrowserSubmitter.submit(
            page=page,
            authorization=auth_mismatch,
            application_id="app_123",
        )
    assert "belongs to application" in str(excinfo.value).lower()


def test_ambiguous_submission_never_retried_automatically():
    status, conf_type, conf_ref, warnings = SubmissionConfirmationDetector.detect_from_content(
        url="https://portal.com/apply",
        page_text="Welcome to the careers landing page.",
    )
    assert status == ConfirmationStatus.UNKNOWN
    assert conf_type == "AMBIGUOUS_POST_SUBMISSION"
    assert len(warnings) > 0

    # Strict invariant: safe retry policy prohibits retrying ambiguous submission
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.SUBMISSION_UNKNOWN) is False
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.CHALLENGE) is False
    assert RetryPolicy.is_action_retryable(PortalErrorCategory.AUTHENTICATION) is False
