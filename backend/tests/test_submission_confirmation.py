import pytest
from app.services.submission.confirmation import SubmissionConfirmationDetector
from app.services.submission.models import ConfirmationStatus


def test_url_and_text_confirmation():
    url = "https://boards.greenhouse.io/acme/jobs/123/thank-you"
    text = "Thank you for applying! Your application has been received."

    status, conf_type, conf_ref, warnings = SubmissionConfirmationDetector.detect_from_content(
        url=url,
        page_text=text,
    )
    assert status == ConfirmationStatus.CONFIRMED
    assert conf_type == "URL_AND_TEXT_CONFIRMATION"
    assert len(warnings) == 0


def test_text_only_confirmation():
    url = "https://jobs.lever.co/company/apply"
    text = "Congratulations, your application was submitted successfully."

    status, conf_type, _, _ = SubmissionConfirmationDetector.detect_from_content(
        url=url,
        page_text=text,
    )
    assert status == ConfirmationStatus.CONFIRMED
    assert conf_type == "TEXT_CONFIRMATION"


def test_url_only_confirmation():
    url = "https://company.com/careers/application-received"
    text = "Welcome to our careers network."

    status, conf_type, _, _ = SubmissionConfirmationDetector.detect_from_content(
        url=url,
        page_text=text,
    )
    assert status == ConfirmationStatus.CONFIRMED
    assert conf_type == "URL_CONFIRMATION"


def test_confirmation_reference_extraction():
    url = "https://boards.greenhouse.io/acme/confirmation"
    text = "Thank you for applying! Your confirmation # is APP-2024-99882. We will review your profile."

    status, _, conf_ref, _ = SubmissionConfirmationDetector.detect_from_content(
        url=url,
        page_text=text,
    )
    assert status == ConfirmationStatus.CONFIRMED
    assert conf_ref == "APP-2024-99882"


def test_error_banner_detection():
    url = "https://jobs.lever.co/company/job"
    text = "Please fix the following errors before submitting: This field is required."

    status, conf_type, _, warnings = SubmissionConfirmationDetector.detect_from_content(
        url=url,
        page_text=text,
    )
    assert status == ConfirmationStatus.NOT_CONFIRMED
    assert conf_type == "ERROR_BANNER_DETECTED"
    assert len(warnings) > 0


def test_ambiguous_outcome_detection():
    url = "https://jobs.lever.co/company/job"
    text = "General company description and header text."

    status, conf_type, _, warnings = SubmissionConfirmationDetector.detect_from_content(
        url=url,
        page_text=text,
    )
    assert status == ConfirmationStatus.UNKNOWN
    assert conf_type == "AMBIGUOUS_POST_SUBMISSION"
    assert len(warnings) > 0
