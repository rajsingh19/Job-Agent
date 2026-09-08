from datetime import datetime, timezone
from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationField,
    DraftCustomQuestion,
    FieldSource,
    FieldType,
    QuestionCategory,
)
from app.schemas.connector import ApplicationMethod, PlatformType
from app.services.browser.enums import FieldActionType, FieldMatchStatus
from app.services.browser.field_detector import FieldDetector
from app.services.browser.models import BrowserField, DiscoveredForm


def test_field_detector_mapping_and_sensitive_protection():
    """Verifies that discovered DOM fields are correctly matched with Phase 6 draft data, and sensitive fields are protected."""
    draft = ApplicationDraft(
        id="app_123",
        user_id="user_123",
        job_id="job_123",
        resume_id="res_123",
        platform=PlatformType.GREENHOUSE,
        application_method=ApplicationMethod.BROWSER,
        fields=[
            ApplicationField(field_id="first_name", label="First Name", field_type=FieldType.TEXT, value="Ada", source=FieldSource.CANDIDATE_PROFILE),
            ApplicationField(field_id="email", label="Email", field_type=FieldType.EMAIL, value="ada@example.com", source=FieldSource.CANDIDATE_PROFILE),
            ApplicationField(field_id="phone", label="Phone", field_type=FieldType.PHONE, value="+15551234567", source=FieldSource.CANDIDATE_PROFILE),
        ],
        custom_questions=[
            DraftCustomQuestion(
                question_id="q_auth_1",
                question="Are you legally authorized to work in the United States?",
                category=QuestionCategory.WORK_AUTHORIZATION,
                answer=None,
                requires_user_input=True,
                user_input_reason="Work authorization requires explicit confirmation.",
            )
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    discovered_form = DiscoveredForm(
        form_id="form_test",
        fields=[
            BrowserField(field_id="first_name", label="First Name", selector="#first_name", input_type="text"),
            BrowserField(field_id="email", label="Email Address", selector="#email", input_type="email"),
            BrowserField(field_id="resume", label="Upload Resume", selector="#resume", input_type="file"),
            BrowserField(field_id="auth", label="Are you legally authorized to work in the United States?", selector="#auth", input_type="text", required=True),
            BrowserField(field_id="unknown_fav_color", label="What is your favorite color?", selector="#color", input_type="text", required=True),
        ]
    )

    plan = FieldDetector.map_fields_to_plan(discovered_form, draft, application_id="app_123")
    actions = plan.actions

    # 1. First Name -> MATCHED, value = "Ada"
    act_fn = next(a for a in actions if a.field_id == "first_name")
    assert act_fn.match_status == FieldMatchStatus.MATCHED
    assert act_fn.value == "Ada"
    assert act_fn.action_type == FieldActionType.FILL

    # 2. Email -> MATCHED, value = "ada@example.com"
    act_em = next(a for a in actions if a.field_id == "email")
    assert act_em.match_status == FieldMatchStatus.MATCHED
    assert act_em.value == "ada@example.com"

    # 3. Resume -> UPLOAD_RESUME, value = "res_123"
    act_res = next(a for a in actions if a.field_id == "resume")
    assert act_res.action_type == FieldActionType.UPLOAD_RESUME
    assert act_res.value == "res_123"

    # 4. Work authorization -> SENSITIVE, requires_user_input = True
    act_auth = next(a for a in actions if a.field_id == "auth")
    assert act_auth.requires_user_input is True

    # 5. Unknown required question -> UNKNOWN, requires_user_input = True
    act_col = next(a for a in actions if a.field_id == "unknown_fav_color")
    assert act_col.match_status == FieldMatchStatus.UNKNOWN
    assert act_col.requires_user_input is True
