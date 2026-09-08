import logging
import re
from typing import Dict, List, Optional, Tuple
from app.schemas.application_draft import ApplicationDraft, ApplicationField, DraftCustomQuestion, QuestionCategory
from app.services.applications.field_mapper import ApplicationFieldMapper
from app.services.applications.field_types import FieldType
from app.services.applications.question_classifier import QuestionClassifier
from app.services.browser.enums import FieldActionType, FieldMatchStatus
from app.services.browser.models import BrowserExecutionPlan, BrowserField, DiscoveredForm, FieldExecutionAction

logger = logging.getLogger(__name__)

# Sensitive categories from Phase 6 that must NEVER be guessed or autofilled without explicit user consent
SENSITIVE_CATEGORIES = {
    QuestionCategory.WORK_AUTHORIZATION,
    QuestionCategory.SALARY,
}

AUTOCOMPLETE_MAP: Dict[str, str] = {
    "given-name": "first_name",
    "family-name": "last_name",
    "name": "full_name",
    "email": "email",
    "tel": "phone",
    "address-level2": "location",
    "url": "portfolio_url",
}


class FieldDetector:
    """
    Maps visible browser form fields to the Phase 6 ApplicationDraft.
    Enforces strict sensitive field protection and human review boundaries.
    """
    _field_mapper = ApplicationFieldMapper()

    @classmethod
    def map_fields_to_plan(
        cls,
        form: DiscoveredForm,
        draft: ApplicationDraft,
        application_id: str,
        step_name: str = "Step 1",
    ) -> BrowserExecutionPlan:
        """
        Synthesizes discovered fields with Phase 6 draft data into an actionable BrowserExecutionPlan.
        """
        # Create lookup maps from Phase 6 draft
        draft_fields_by_key: Dict[str, ApplicationField] = {
            f.field_id: f for f in draft.fields if f.value
        }
        draft_questions_by_prompt: Dict[str, DraftCustomQuestion] = {
            q.question.strip().lower(): q for q in draft.custom_questions
        }

        actions: List[FieldExecutionAction] = []

        for field in form.fields:
            if not field.visible or not field.enabled:
                continue

            action = cls._map_single_field(
                field=field,
                draft=draft,
                draft_fields=draft_fields_by_key,
                draft_questions=draft_questions_by_prompt,
            )
            actions.append(action)

        return BrowserExecutionPlan(
            application_id=application_id,
            step_name=step_name,
            actions=actions,
        )

    @classmethod
    def _map_single_field(
        cls,
        field: BrowserField,
        draft: ApplicationDraft,
        draft_fields: Dict[str, ApplicationField],
        draft_questions: Dict[str, DraftCustomQuestion],
    ) -> FieldExecutionAction:
        """
        Maps an individual browser field into a planned action with safety classifications.
        """
        # 1. Check for file upload (Resume)
        if field.input_type == "file":
            label_lower = (field.label or field.name or "").lower()
            if "resume" in label_lower or "cv" in label_lower or not field.label:
                return FieldExecutionAction(
                    field_id=field.field_id,
                    selector=field.selector,
                    action_type=FieldActionType.UPLOAD_RESUME,
                    value=draft.resume_id,
                    value_source="PHASE_6_RESUME",
                    match_status=FieldMatchStatus.MATCHED,
                    requires_user_input=False,
                )
            else:
                return FieldExecutionAction(
                    field_id=field.field_id,
                    selector=field.selector,
                    action_type=FieldActionType.SKIP,
                    match_status=FieldMatchStatus.UNKNOWN,
                    requires_user_input=field.required,
                    user_input_reason=f"Unknown file upload requirement: {field.label or field.name}",
                )

        # 2. Check Autocomplete Attribute
        target_canonical_key: Optional[str] = None
        if field.autocomplete and field.autocomplete in AUTOCOMPLETE_MAP:
            target_canonical_key = AUTOCOMPLETE_MAP[field.autocomplete]

        # 3. Check Normalized Label with ApplicationFieldMapper
        normalized_label = (field.label or field.placeholder or field.name or "").strip()
        if not target_canonical_key and normalized_label:
            canonical_key, _ = cls._field_mapper.identify_canonical_field(normalized_label)
            target_canonical_key = canonical_key

        # 4. Standard Draft Field Match
        if target_canonical_key and target_canonical_key in draft_fields:
            draft_f = draft_fields[target_canonical_key]
            action_type = FieldActionType.SELECT if field.input_type == "select" else FieldActionType.FILL
            return FieldExecutionAction(
                field_id=field.field_id,
                selector=field.selector,
                action_type=action_type,
                value=str(draft_f.value),
                value_source=draft_f.source.value,
                match_status=FieldMatchStatus.MATCHED,
                requires_user_input=(draft_f.value is None and draft_f.required),
                user_input_reason=draft_f.warning,
            )

        # 5. Check Custom Questions in Draft
        if normalized_label:
            # Check exact or substring match in draft custom questions
            norm_lower = normalized_label.lower()
            matched_q: Optional[DraftCustomQuestion] = None
            for q_prompt, q_obj in draft_questions.items():
                if q_prompt in norm_lower or norm_lower in q_prompt:
                    matched_q = q_obj
                    break

            if matched_q:
                # If question category is sensitive and requires user input, do NOT autofill!
                if matched_q.category in SENSITIVE_CATEGORIES and matched_q.requires_user_input:
                    return FieldExecutionAction(
                        field_id=field.field_id,
                        selector=field.selector,
                        action_type=FieldActionType.SKIP,
                        value=matched_q.answer,
                        value_source="PHASE_6_CUSTOM_QUESTION",
                        match_status=FieldMatchStatus.REQUIRES_USER_INPUT,
                        requires_user_input=True,
                        user_input_reason=f"Sensitive question ({matched_q.category.value}) requires explicit user input.",
                    )

                if matched_q.answer is not None:
                    action_type = FieldActionType.SELECT if field.input_type == "select" else (
                        FieldActionType.CHECK if field.input_type in ("checkbox", "radio") else FieldActionType.FILL
                    )
                    return FieldExecutionAction(
                        field_id=field.field_id,
                        selector=field.selector,
                        action_type=action_type,
                        value=str(matched_q.answer),
                        value_source="PHASE_6_CUSTOM_QUESTION",
                        match_status=FieldMatchStatus.MATCHED,
                        requires_user_input=matched_q.requires_user_input,
                        user_input_reason=matched_q.user_input_reason,
                    )

            # 6. Check with QuestionClassifier for sensitive signals not in draft
            detected_category = QuestionClassifier.classify(normalized_label)
            if detected_category in SENSITIVE_CATEGORIES:
                return FieldExecutionAction(
                    field_id=field.field_id,
                    selector=field.selector,
                    action_type=FieldActionType.SKIP,
                    match_status=FieldMatchStatus.REQUIRES_USER_INPUT,
                    requires_user_input=True,
                    user_input_reason=f"Sensitive question ({detected_category.value}) detected on page.",
                )

        # 7. Unmatched / Unknown Field
        return FieldExecutionAction(
            field_id=field.field_id,
            selector=field.selector,
            action_type=FieldActionType.SKIP,
            match_status=FieldMatchStatus.UNKNOWN,
            requires_user_input=field.required,
            user_input_reason=f"Unknown field requires manual entry: {normalized_label}" if field.required else None,
        )
