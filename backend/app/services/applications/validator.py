import re
from typing import List
from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationDraftValidationResponse,
    CandidateApplicationContext,
    FieldType,
)


class ApplicationDraftValidator:
    """
    Validates application drafts prior to user presentation and browser automation.
    Ensures structural integrity, data format compliance, and anti-fabrication truthfulness.
    """

    EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    URL_REGEX = r"^(?:https?:\/\/)?(?:www\.)?[\w\.-]+\.[a-zA-Z]{2,}(?:\/.*)?$"

    @classmethod
    def validate_draft(
        cls,
        draft: ApplicationDraft,
        context: CandidateApplicationContext,
    ) -> ApplicationDraftValidationResponse:
        missing_fields: List[str] = []
        validation_errors: List[str] = []
        warnings: List[str] = list(draft.warnings)
        requires_user_input: bool = draft.requires_user_input

        # 1. Validate Resume Selection
        if not draft.resume_id:
            validation_errors.append("Application draft must specify a valid selected resume.")

        # 2. Validate Standard Form Fields
        for field in draft.fields:
            val_str = str(field.value).strip() if field.value is not None else ""

            if field.required and not val_str:
                missing_fields.append(field.label)
                validation_errors.append(f"Required field '{field.label}' is missing a value.")
                requires_user_input = True

            # Format validations if value is present
            if val_str:
                if field.field_type == FieldType.EMAIL and not re.match(cls.EMAIL_REGEX, val_str):
                    validation_errors.append(f"Invalid email format: '{val_str}'")
                elif field.field_type == FieldType.URL and not re.match(cls.URL_REGEX, val_str):
                    validation_errors.append(f"Invalid URL format for '{field.label}': '{val_str}'")
                elif field.field_type == FieldType.PHONE:
                    digits = re.sub(r"\D", "", val_str)
                    if len(digits) < 7:
                        validation_errors.append(f"Phone number '{val_str}' contains fewer than 7 digits.")

        # 3. Validate Custom Questions
        for q in draft.custom_questions:
            if q.required and not q.answer and not q.requires_user_input:
                validation_errors.append(f"Question '{q.question}' has neither an answer nor user-input flag.")
            if q.requires_user_input:
                requires_user_input = True

        # 4. Truthfulness / Anti-Fabrication Check
        # Ensure answers don't claim certifications or employers not in candidate context
        cand_companies = {
            exp.get("company", "").lower()
            for exp in context.experience
            if exp.get("company")
        }
        for q in draft.custom_questions:
            ans = q.answer or ""
            # If answer specifically states "worked at X", check against context
            for match in re.finditer(r"worked at ([a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+){0,2})", ans, re.IGNORECASE):
                claimed_comp = match.group(1).strip()
                claimed_lower = claimed_comp.lower()
                if claimed_comp and not any(claimed_lower in c or c in claimed_lower for c in cand_companies):
                    warnings.append(f"Claimed employer '{claimed_comp}' not verified in candidate work history.")

        is_valid = len(validation_errors) == 0
        ready_for_review = is_valid

        return ApplicationDraftValidationResponse(
            application_id=draft.id,
            is_valid=is_valid,
            ready_for_review=ready_for_review,
            requires_user_input=requires_user_input,
            missing_fields=missing_fields,
            validation_errors=validation_errors,
            warnings=warnings,
        )
