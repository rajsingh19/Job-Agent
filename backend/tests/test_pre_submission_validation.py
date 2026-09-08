import pytest
from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationField,
    CandidateApplicationContext,
    DraftCustomQuestion,
    FieldType,
)
from app.schemas.connector import ApplicationMethod, PlatformType
from app.services.applications.validator import ApplicationDraftValidator
from app.services.submission.approval_validator import ApprovalValidator


def create_base_draft():
    return ApplicationDraft(
        id="app_pre_val",
        user_id="user_val",
        job_id="job_val",
        resume_id="res_val",
        platform=PlatformType.GREENHOUSE,
        application_method=ApplicationMethod.ATS,
        fields=[
            ApplicationField(field_id="full_name", label="Full Name", value="Bob Developer", field_type=FieldType.TEXT, required=True),
            ApplicationField(field_id="email", label="Email", value="bob@example.com", field_type=FieldType.EMAIL, required=True),
            ApplicationField(field_id="phone", label="Phone", value="+1-555-234-5678", field_type=FieldType.PHONE, required=True),
            ApplicationField(field_id="website", label="Portfolio", value="https://bobdev.io", field_type=FieldType.URL, required=False),
        ],
        custom_questions=[
            DraftCustomQuestion(
                question_id="q1",
                question="Why join our team?",
                answer="I have relevant experience and passion for your product.",
                confidence=0.9,
            )
        ],
    )


def test_valid_draft_passes_pre_submission():
    draft = create_base_draft()
    is_valid, errors = ApprovalValidator.validate_for_approval(draft)
    assert is_valid is True
    assert len(errors) == 0


def test_missing_resume_fails_pre_submission():
    draft = create_base_draft()
    draft.resume_id = ""
    is_valid, errors = ApprovalValidator.validate_for_approval(draft)
    assert is_valid is False
    assert any("resume" in err.lower() for err in errors)


def test_invalid_email_format_fails():
    draft = create_base_draft()
    for f in draft.fields:
        if f.field_id == "email":
            f.value = "not-an-email"
    is_valid, errors = ApprovalValidator.validate_for_approval(draft)
    assert is_valid is False
    assert any("email" in err.lower() for err in errors)


def test_invalid_url_format_fails():
    draft = create_base_draft()
    for f in draft.fields:
        if f.field_id == "website":
            f.value = "htp:/invalid url @@"
    is_valid, errors = ApprovalValidator.validate_for_approval(draft)
    assert is_valid is False
    assert any("url" in err.lower() for err in errors)


def test_short_phone_fails():
    draft = create_base_draft()
    for f in draft.fields:
        if f.field_id == "phone":
            f.value = "12345"  # Fewer than 7 digits
    is_valid, errors = ApprovalValidator.validate_for_approval(draft)
    assert is_valid is False
    assert any("phone" in err.lower() for err in errors)


def test_unresolved_user_input_fails():
    draft = create_base_draft()
    draft.custom_questions.append(
        DraftCustomQuestion(
            question_id="q_clearance",
            question="Security Clearance Level?",
            answer=None,
            requires_user_input=True,
            required=True,
        )
    )
    is_valid, errors = ApprovalValidator.validate_for_approval(draft)
    assert is_valid is False
    assert any("unresolved" in err.lower() for err in errors)


def test_truthfulness_warning_on_unverified_employer():
    draft = create_base_draft()
    draft.custom_questions[0].answer = "I previously worked at NASA on Mars Rovers."

    context = CandidateApplicationContext(
        name="Bob",
        email="bob@example.com",
        skills=["Python"],
        experience=[{"company": "Local Startup", "role": "Engineer"}],
    )

    resp = ApplicationDraftValidator.validate_draft(draft=draft, context=context)
    assert any("NASA" in w for w in resp.warnings)
