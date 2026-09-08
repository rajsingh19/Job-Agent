import pytest
from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationField,
    DraftCustomQuestion,
    FieldType,
)
from app.schemas.connector import ApplicationMethod, PlatformType
from app.services.submission.approval_validator import ApprovalValidator


def create_sample_draft(
    app_id: str = "app_123",
    job_id: str = "job_456",
    resume_id: str = "res_789",
    cover_letter: str = "I am excited to apply.",
    phone: str = "+1-555-1234567",
) -> ApplicationDraft:
    return ApplicationDraft(
        id=app_id,
        user_id="user_1",
        job_id=job_id,
        resume_id=resume_id,
        platform=PlatformType.GREENHOUSE,
        application_method=ApplicationMethod.ATS,
        cover_letter=cover_letter,
        fields=[
            ApplicationField(field_id="full_name", label="Full Name", value="Alice Smith", field_type=FieldType.TEXT),
            ApplicationField(field_id="email", label="Email", value="alice@example.com", field_type=FieldType.EMAIL),
            ApplicationField(field_id="phone", label="Phone", value=phone, field_type=FieldType.PHONE),
        ],
        custom_questions=[
            DraftCustomQuestion(
                question_id="q1",
                question="Years of Python experience?",
                answer="5",
                confidence=1.0,
            ),
            DraftCustomQuestion(
                question_id="q2",
                question="Are you authorized to work in US?",
                answer="Yes",
                confidence=1.0,
            ),
        ],
    )


def test_deterministic_version_hash():
    draft1 = create_sample_draft()
    draft2 = create_sample_draft()

    hash1 = ApprovalValidator.calculate_review_version_hash(draft1)
    hash2 = ApprovalValidator.calculate_review_version_hash(draft2)

    assert hash1 == hash2
    assert len(hash1) == 64


def test_version_hash_independent_of_field_order():
    draft1 = create_sample_draft()
    draft2 = create_sample_draft()

    # Reverse fields and questions
    draft2.fields = list(reversed(draft1.fields))
    draft2.custom_questions = list(reversed(draft1.custom_questions))

    hash1 = ApprovalValidator.calculate_review_version_hash(draft1)
    hash2 = ApprovalValidator.calculate_review_version_hash(draft2)

    assert hash1 == hash2


def test_hash_changes_when_form_field_modified():
    draft_orig = create_sample_draft()
    draft_mod = create_sample_draft(phone="+1-555-9999999")

    hash_orig = ApprovalValidator.calculate_review_version_hash(draft_orig)
    hash_mod = ApprovalValidator.calculate_review_version_hash(draft_mod)

    assert hash_orig != hash_mod


def test_hash_changes_when_cover_letter_modified():
    draft_orig = create_sample_draft()
    draft_mod = create_sample_draft(cover_letter="Updated cover letter content.")

    hash_orig = ApprovalValidator.calculate_review_version_hash(draft_orig)
    hash_mod = ApprovalValidator.calculate_review_version_hash(draft_mod)

    assert hash_orig != hash_mod


def test_hash_changes_when_resume_modified():
    draft_orig = create_sample_draft(resume_id="res_111")
    draft_mod = create_sample_draft(resume_id="res_222")

    hash_orig = ApprovalValidator.calculate_review_version_hash(draft_orig)
    hash_mod = ApprovalValidator.calculate_review_version_hash(draft_mod)

    assert hash_orig != hash_mod


def test_hash_changes_when_question_answer_modified():
    draft_orig = create_sample_draft()
    draft_mod = create_sample_draft()
    draft_mod.custom_questions[0].answer = "10"

    hash_orig = ApprovalValidator.calculate_review_version_hash(draft_orig)
    hash_mod = ApprovalValidator.calculate_review_version_hash(draft_mod)

    assert hash_orig != hash_mod
