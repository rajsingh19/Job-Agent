from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationField,
    CandidateApplicationContext,
    DraftCustomQuestion,
    FieldSource,
    FieldType,
    QuestionCategory,
)
from app.schemas.connector import ApplicationMethod, PlatformType
from app.services.applications.validator import ApplicationDraftValidator


def test_validation_valid_draft():
    context = CandidateApplicationContext(
        name="Morgan Smith",
        email="morgan@example.com",
        phone="+1-555-4321",
        skills=["Python"],
    )

    draft = ApplicationDraft(
        id="draft_val_1",
        user_id="user_val",
        job_id="job_val",
        resume_id="res_val",
        platform=PlatformType.GREENHOUSE,
        application_method=ApplicationMethod.ATS,
        fields=[
            ApplicationField(
                field_id="full_name",
                label="Full Name",
                field_type=FieldType.TEXT,
                value="Morgan Smith",
                required=True,
            ),
            ApplicationField(
                field_id="email",
                label="Email",
                field_type=FieldType.EMAIL,
                value="morgan@example.com",
                required=True,
            ),
            ApplicationField(
                field_id="phone",
                label="Phone",
                field_type=FieldType.PHONE,
                value="+1-555-4321",
                required=True,
            ),
        ],
        custom_questions=[
            DraftCustomQuestion(
                question_id="q1",
                question="Graduation Year?",
                category=QuestionCategory.EDUCATION,
                answer="2024",
                required=True,
            )
        ],
        missing_fields=[],
        warnings=[],
        validation_errors=[],
        ready_for_review=True,
        requires_user_input=False,
    )

    report = ApplicationDraftValidator.validate_draft(draft, context)
    assert report.is_valid is True
    assert report.ready_for_review is True
    assert report.requires_user_input is False
    assert len(report.validation_errors) == 0


def test_validation_missing_required_fields_and_formats():
    context = CandidateApplicationContext(
        name="Morgan Smith",
        email="morgan@example.com",
        skills=[],
    )

    draft = ApplicationDraft(
        id="draft_val_2",
        user_id="user_val",
        job_id="job_val",
        resume_id="",  # Missing resume
        platform=PlatformType.LEVER,
        application_method=ApplicationMethod.ATS,
        fields=[
            ApplicationField(
                field_id="full_name",
                label="Full Name",
                field_type=FieldType.TEXT,
                value="",  # Missing required field
                required=True,
            ),
            ApplicationField(
                field_id="email",
                label="Email",
                field_type=FieldType.EMAIL,
                value="not-an-email",  # Invalid email format
                required=True,
            ),
            ApplicationField(
                field_id="phone",
                label="Phone",
                field_type=FieldType.PHONE,
                value="123",  # Too short phone
                required=True,
            ),
            ApplicationField(
                field_id="portfolio_url",
                label="Portfolio URL",
                field_type=FieldType.URL,
                value="htp:/bad-url",  # Malformed URL
                required=False,
            ),
        ],
        custom_questions=[],
        missing_fields=[],
        warnings=[],
        validation_errors=[],
        ready_for_review=False,
        requires_user_input=False,
    )

    report = ApplicationDraftValidator.validate_draft(draft, context)
    assert report.is_valid is False
    assert report.ready_for_review is False
    assert report.requires_user_input is True
    assert "Full Name" in report.missing_fields
    assert any("Invalid email format" in err for err in report.validation_errors)
    assert any("valid selected resume" in err for err in report.validation_errors)


def test_validation_unresolved_sensitive_question_flags_user_input():
    context = CandidateApplicationContext(name="Morgan", email="morgan@example.com", skills=[])
    draft = ApplicationDraft(
        id="draft_val_3",
        user_id="user_val",
        job_id="job_val",
        resume_id="res_val",
        platform=PlatformType.ASHBY,
        application_method=ApplicationMethod.ATS,
        fields=[],
        custom_questions=[
            DraftCustomQuestion(
                question_id="q_auth",
                question="Are you authorized to work in the US?",
                category=QuestionCategory.WORK_AUTHORIZATION,
                answer=None,
                required=True,
                requires_user_input=True,
            )
        ],
        missing_fields=[],
        warnings=[],
        validation_errors=[],
        ready_for_review=False,
        requires_user_input=True,
    )

    report = ApplicationDraftValidator.validate_draft(draft, context)
    assert report.requires_user_input is True


def test_validation_truthfulness_warning_unverified_employer():
    context = CandidateApplicationContext(
        name="Morgan",
        email="morgan@example.com",
        skills=[],
        experience=[{"company": "Verified Company LLC", "role": "Developer"}],
    )
    draft = ApplicationDraft(
        id="draft_val_4",
        user_id="user_val",
        job_id="job_val",
        resume_id="res_val",
        platform=PlatformType.GREENHOUSE,
        application_method=ApplicationMethod.ATS,
        fields=[],
        custom_questions=[
            DraftCustomQuestion(
                question_id="q_exp",
                question="Tell us about your background",
                category=QuestionCategory.EXPERIENCE,
                answer="I previously worked at SpaceRocket Corp developing rocket telemetry.",
                required=True,
                requires_user_input=False,
            )
        ],
        missing_fields=[],
        warnings=[],
        validation_errors=[],
        ready_for_review=True,
        requires_user_input=False,
    )

    report = ApplicationDraftValidator.validate_draft(draft, context)
    assert any("SpaceRocket Corp" in w for w in report.warnings)
