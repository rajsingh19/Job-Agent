import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationDraftValidationResponse,
    ApplicationReviewPackageResponse,
)
from app.services.applications.cover_letter import CoverLetterGenerator
from app.services.applications.field_mapper import ApplicationFieldMapper
from app.services.applications.models import build_candidate_application_context
from app.services.applications.question_answerer import QuestionAnswerer
from app.services.applications.resume_selector import ResumeSelector
from app.services.applications.review_package import ReviewPackageGenerator
from app.services.applications.validator import ApplicationDraftValidator
from app.services.connectors.router import ConnectorRouter, get_connector_router
from app.services.profile.service import CandidateProfileService

logger = logging.getLogger(__name__)


class ApplicationDraftService:
    """
    Coordinates application draft creation, field mapping, truthful Q&A generation,
    validation, and review package persistence.
    """

    def __init__(
        self,
        profile_service: Optional[CandidateProfileService] = None,
        connector_router: Optional[ConnectorRouter] = None,
        field_mapper: Optional[ApplicationFieldMapper] = None,
        question_answerer: Optional[QuestionAnswerer] = None,
        cover_letter_gen: Optional[CoverLetterGenerator] = None,
    ):
        self.profile_service = profile_service or CandidateProfileService()
        self.connector_router = connector_router or get_connector_router()
        self.field_mapper = field_mapper or ApplicationFieldMapper()
        self.question_answerer = question_answerer or QuestionAnswerer()
        self.cover_letter_gen = cover_letter_gen or CoverLetterGenerator()

    async def create_draft(
        self,
        db: AsyncSession,
        user_id: str,
        job_id: str,
        resume_id: Optional[str] = None,
        custom_questions: Optional[List[Dict[str, Any]]] = None,
        include_cover_letter: bool = True,
        explicit_user_inputs: Optional[Dict[str, Any]] = None,
    ) -> ApplicationDraft:
        # 1. Fetch Job
        job_res = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
        job = job_res.scalars().first()
        if not job:
            raise ValueError(f"Job posting with ID '{job_id}' not found.")

        # 2. Fetch Candidate Profile & Available Resumes
        cand_profile = await self.profile_service.get_candidate_profile(db=db, user_id=user_id)

        resumes_res = await db.execute(select(Resume).where(Resume.user_id == user_id))
        available_resumes = list(resumes_res.scalars().all())
        if not available_resumes:
            raise ValueError(f"No resumes available for user '{user_id}'. Please upload a resume first.")

        # 3. Select Resume
        selected_res = ResumeSelector.select_resume(
            user_id=user_id,
            candidate_profile=cand_profile,
            job=job,
            available_resumes=available_resumes,
            requested_resume_id=resume_id,
        )
        selected_resume_obj = next(r for r in available_resumes if str(r.id) == selected_res.resume_id)

        # 4. Fetch User Preferences
        pref_res = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        user_pref = pref_res.scalars().first()

        # 5. Resolve Application Route
        route = await self.connector_router.route_job(job)

        # 6. Build Candidate Application Context
        context = build_candidate_application_context(
            candidate_profile=cand_profile,
            resume=selected_resume_obj,
            preferences=user_pref,
        )

        # 7. Map Standard Fields
        fields = self.field_mapper.map_standard_fields(
            context=context,
            explicit_user_inputs=explicit_user_inputs,
        )

        # 8. Answer Custom Questions
        answered_questions = []
        if custom_questions:
            answered_questions = await self.question_answerer.answer_questions(
                questions=custom_questions,
                context=context,
                job=job,
                explicit_user_answers=explicit_user_inputs,
            )

        # 9. Generate Cover Letter
        cover_letter = None
        warnings: List[str] = []
        if selected_res.requires_user_input:
            warnings.append(selected_res.selection_reason)

        if include_cover_letter:
            letter_text, letter_warning = await self.cover_letter_gen.generate_cover_letter(
                context=context,
                job=job,
            )
            cover_letter = letter_text
            if letter_warning:
                warnings.append(letter_warning)

        # 10. Check Existing or Create Application Record
        app_res = await db.execute(
            select(Application).where(Application.user_id == user_id, Application.job_id == job_id)
        )
        application = app_res.scalars().first()

        if not application:
            application = Application(
                id=f"app_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                job_id=job_id,
                resume_id=selected_res.resume_id,
                connector=route.connector,
                status=ApplicationStatus.DRAFTING.value,
            )
            db.add(application)
            await db.flush()
        else:
            application.resume_id = selected_res.resume_id
            application.connector = route.connector

        # 11. Assemble Draft and Validate
        preliminary_draft = ApplicationDraft(
            id=str(application.id),
            user_id=user_id,
            job_id=job_id,
            resume_id=selected_res.resume_id,
            platform=route.platform,
            application_method=route.application_method,
            fields=fields,
            custom_questions=answered_questions,
            cover_letter=cover_letter,
            missing_fields=[],
            warnings=warnings,
            validation_errors=[],
            ready_for_review=False,
            requires_user_input=selected_res.requires_user_input,
            created_at=application.created_at or datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        validation = ApplicationDraftValidator.validate_draft(draft=preliminary_draft, context=context)

        # Finalize Draft Status
        final_draft = ApplicationDraft(
            id=str(application.id),
            user_id=user_id,
            job_id=job_id,
            resume_id=selected_res.resume_id,
            platform=route.platform,
            application_method=route.application_method,
            fields=fields,
            custom_questions=answered_questions,
            cover_letter=cover_letter,
            missing_fields=validation.missing_fields,
            warnings=validation.warnings,
            validation_errors=validation.validation_errors,
            ready_for_review=validation.ready_for_review,
            requires_user_input=validation.requires_user_input,
            created_at=application.created_at or datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # 12. Persist to Application
        if final_draft.requires_user_input:
            application.status = ApplicationStatus.REQUIRES_USER_ACTION.value
        elif final_draft.ready_for_review:
            application.status = ApplicationStatus.PENDING_REVIEW.value
        else:
            application.status = ApplicationStatus.DRAFTING.value

        application.review_package = final_draft.model_dump(mode="json")
        application.generated_answers = {
            q.question_id: q.answer for q in final_draft.custom_questions if q.answer
        }
        application.warnings = final_draft.warnings

        await db.commit()
        await db.refresh(application)

        return final_draft

    async def get_draft(
        self,
        db: AsyncSession,
        user_id: str,
        application_id: str,
    ) -> ApplicationDraft:
        app_res = await db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user_id)
        )
        application = app_res.scalars().first()
        if not application:
            raise ValueError(f"Application with ID '{application_id}' not found for user '{user_id}'.")

        if not application.review_package:
            raise ValueError(f"Application draft has not been initialized for application '{application_id}'.")

        return ApplicationDraft.model_validate(application.review_package)

    async def validate_draft(
        self,
        db: AsyncSession,
        user_id: str,
        application_id: str,
    ) -> ApplicationDraftValidationResponse:
        draft = await self.get_draft(db=db, user_id=user_id, application_id=application_id)
        cand_profile = await self.profile_service.get_candidate_profile(db=db, user_id=user_id)
        context = build_candidate_application_context(candidate_profile=cand_profile)
        return ApplicationDraftValidator.validate_draft(draft=draft, context=context)

    async def get_review_package(
        self,
        db: AsyncSession,
        user_id: str,
        application_id: str,
    ) -> ApplicationReviewPackageResponse:
        draft = await self.get_draft(db=db, user_id=user_id, application_id=application_id)

        job_res = await db.execute(select(JobPosting).where(JobPosting.id == draft.job_id))
        job = job_res.scalars().first()
        if not job:
            raise ValueError(f"Associated job '{draft.job_id}' not found.")

        resume_res = await db.execute(select(Resume).where(Resume.id == draft.resume_id))
        resume = resume_res.scalars().first()

        return ReviewPackageGenerator.generate_review_package(
            draft=draft,
            job=job,
            resume=resume,
        )
