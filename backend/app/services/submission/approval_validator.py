import hashlib
import json
import logging
from typing import List, Optional, Tuple
from app.schemas.application_draft import ApplicationDraft, CandidateApplicationContext
from app.services.applications.validator import ApplicationDraftValidator

logger = logging.getLogger(__name__)


class ApprovalValidator:
    """
    Validates application readiness and calculates deterministic content version hashes.
    Guarantees that candidates approve the exact application version that will be submitted.
    """

    @classmethod
    def calculate_review_version_hash(cls, draft: ApplicationDraft) -> str:
        """
        Calculates a deterministic SHA-256 hash of all submission-relevant draft content.
        Excludes non-semantic fields such as timestamps or transient flags.
        """
        # 1. Normalize fields (sorted by field_id)
        norm_fields = sorted(
            [{"id": f.field_id, "val": str(f.value) if f.value is not None else ""} for f in draft.fields],
            key=lambda x: x["id"]
        )

        # 2. Normalize custom questions (sorted by question_id)
        norm_questions = sorted(
            [{"id": q.question_id, "prompt": q.question.strip().lower(), "ans": str(q.answer) if q.answer is not None else ""}
             for q in draft.custom_questions],
            key=lambda x: x["id"]
        )

        # 3. Assemble canonical payload
        payload = {
            "app_id": draft.id,
            "job_id": draft.job_id,
            "resume_id": draft.resume_id or "",
            "cover_letter": (draft.cover_letter or "").strip(),
            "fields": norm_fields,
            "questions": norm_questions,
        }

        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def validate_for_approval(
        cls,
        draft: ApplicationDraft,
        context: Optional[CandidateApplicationContext] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Re-validates the draft to ensure complete readiness before approval can be granted.
        Returns (is_valid, list_of_blocking_errors).
        """
        errors: List[str] = []

        # 1. Run standard draft validator
        val_resp = ApplicationDraftValidator.validate_draft(draft=draft, context=context)
        if val_resp.validation_errors:
            errors.extend(val_resp.validation_errors)

        if val_resp.missing_fields:
            errors.append(f"Missing required fields: {', '.join(val_resp.missing_fields)}")

        # 2. Check unresolved user input requirements
        if draft.requires_user_input or val_resp.requires_user_input:
            errors.append("Application has unresolved questions or fields requiring candidate attention.")

        for q in draft.custom_questions:
            if q.requires_user_input:
                errors.append(f"Unresolved question requires answer: '{q.question}'")

        # 3. Ensure resume is selected
        if not draft.resume_id:
            errors.append("No resume is selected for this application.")

        is_valid = len(errors) == 0
        return is_valid, errors
