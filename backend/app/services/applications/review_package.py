from typing import List, Optional
from app.models.job import JobPosting
from app.models.resume import Resume
from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationReviewPackageResponse,
)
from app.schemas.job import JobPostingResponse
from app.schemas.resume import ResumeResponse


class ReviewPackageGenerator:
    """
    Assembles consolidated human-in-the-loop review packages from application drafts.
    Makes it easy for users to inspect all populated fields, custom answers, and warnings
    prior to any automated application actions.
    """

    @staticmethod
    def generate_review_package(
        draft: ApplicationDraft,
        job: JobPosting,
        resume: Optional[Resume] = None,
        screenshots: Optional[List[str]] = None,
    ) -> ApplicationReviewPackageResponse:
        job_resp = JobPostingResponse.model_validate(job)
        resume_resp = ResumeResponse.model_validate(resume) if resume else None

        user_action_reason = None
        if draft.requires_user_input:
            if draft.missing_fields:
                user_action_reason = f"Missing required fields: {', '.join(draft.missing_fields)}"
            elif any(q.requires_user_input for q in draft.custom_questions):
                unresolved = [q.question for q in draft.custom_questions if q.requires_user_input]
                user_action_reason = f"Questions requiring explicit user input: {'; '.join(unresolved)}"
            elif draft.validation_errors:
                user_action_reason = f"Validation errors: {'; '.join(draft.validation_errors)}"

        return ApplicationReviewPackageResponse(
            application_id=draft.id,
            user_id=draft.user_id,
            job=job_resp,
            selected_resume=resume_resp,
            platform=draft.platform,
            application_method=draft.application_method,
            fields=draft.fields,
            custom_questions=draft.custom_questions,
            cover_letter=draft.cover_letter,
            missing_fields=draft.missing_fields,
            warnings=draft.warnings,
            validation_errors=draft.validation_errors,
            ready_for_review=draft.ready_for_review,
            requires_user_input=draft.requires_user_input,
            screenshots=screenshots or [],
            requires_user_action_reason=user_action_reason,
        )
