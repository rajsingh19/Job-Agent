import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.job import JobPosting
from app.schemas.application_draft import ApplicationDraft
from app.services.browser.auth_detector import AuthDetector
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.challenge_detector import ChallengeDetector
from app.services.browser.enums import (
    AuthStatus,
    BrowserSessionStatus,
    ChallengeType,
    ExecutionStepState,
    FieldActionType,
)
from app.services.browser.exceptions import (
    BrowserExecutionError,
    BrowserSessionNotFoundError,
    SubmissionBlockedError,
    UserActionRequiredError,
)
from app.services.browser.execution_state import ApplicationExecutionStore
from app.services.browser.field_detector import FieldDetector
from app.services.browser.field_executor import FieldExecutor
from app.services.browser.form_parser import FormParser
from app.services.browser.models import ExecutionStateSnapshot
from app.services.browser.navigation import NavigationHelper
from app.services.browser.resume_uploader import ResumeUploader
from app.services.browser.screenshot_manager import ScreenshotManager
from app.services.browser.session_manager import SessionManager
from app.services.connectors.router import get_connector_router

logger = logging.getLogger(__name__)


class BrowserExecutionService:
    """
    Master orchestrator for Phase 7 browser automation.
    Conducts safe navigation, form inspection, verified field filling, resume upload,
    and checkpoint capture while strictly enforcing human-in-the-loop boundaries.
    """

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        execution_store: Optional[ApplicationExecutionStore] = None,
    ):
        self.session_manager = session_manager or SessionManager.get_instance()
        self.execution_store = execution_store or ApplicationExecutionStore.get_instance()

    async def start_application_execution(
        self,
        db: AsyncSession,
        user_id: str,
        application_id: str,
        session_id: Optional[str] = None,
    ) -> ExecutionStateSnapshot:
        """
        Initiates automated browser execution for an application draft.
        """
        # 1. Fetch Application from DB and verify ownership
        stmt = select(Application).where(Application.id == application_id, Application.user_id == user_id)
        result = await db.execute(stmt)
        application = result.scalars().first()

        if not application:
            raise BrowserExecutionError(f"Application '{application_id}' not found or unauthorized.")

        # Guard: Application must not already be submitting or submitted
        if application.status in (ApplicationStatus.SUBMITTING.value, ApplicationStatus.SUBMITTED.value):
            raise BrowserExecutionError(f"Application is already in '{application.status}' state and cannot be modified.")

        # 2. Verify Phase 6 Draft exists in review_package
        if not application.review_package or "fields" not in application.review_package:
            raise BrowserExecutionError(
                f"Application '{application_id}' does not have a valid Phase 6 draft. Please generate a draft first."
            )

        draft = ApplicationDraft(**application.review_package)

        # 3. Fetch Job for target URL
        job_res = await db.execute(select(JobPosting).where(JobPosting.id == application.job_id))
        job = job_res.scalars().first()
        if not job:
            raise BrowserExecutionError(f"Target job for application '{application_id}' not found.")

        target_url = getattr(job, "apply_url", None) or getattr(job, "source_url", None) or getattr(job, "application_url", None)
        if not target_url:
            raise BrowserExecutionError(f"Job '{job.id}' has no application or posting URL configured.")

        # 4. Initialize or retrieve Browser Session
        if not session_id:
            session_info = await self.session_manager.create_session(user_id=user_id)
            session_id = session_info.session_id
        else:
            session_info = self.session_manager.get_session_record(session_id=session_id, user_id=user_id).to_info()

        bm = await BrowserManager.get_instance()
        session_ctx = bm.get_session(session_id)
        if not session_ctx:
            raise BrowserSessionNotFoundError(f"Active browser session '{session_id}' not found.")

        page = session_ctx.page
        self.execution_store.init_execution(application_id=application_id, session_id=session_id)

        # 5. Navigate to Application URL
        self.execution_store.update_state(
            application_id=application_id,
            state=ExecutionStepState.NAVIGATING,
            current_url=target_url,
            current_step="navigation",
        )
        await NavigationHelper.navigate_to_url(page=page, url=target_url)

        # Checkpoint: After Navigation
        scr_nav = await ScreenshotManager.capture_checkpoint(
            page=page, step="after_navigation", application_id=application_id
        )
        if scr_nav:
            self.execution_store.update_state(application_id=application_id, screenshot=scr_nav)

        # 6. Check Authentication Status
        auth_status = await AuthDetector.detect_auth_status(page)
        if auth_status == AuthStatus.LOGIN_REQUIRED:
            scr_auth = await ScreenshotManager.capture_checkpoint(
                page=page, step="login_required", application_id=application_id
            )
            snapshot = self.execution_store.update_state(
                application_id=application_id,
                state=ExecutionStepState.AUTHENTICATION_REQUIRED,
                auth_status=AuthStatus.LOGIN_REQUIRED,
                user_action_required=True,
                user_action_reason="AUTHENTICATION_REQUIRED",
                user_instructions="Please log in manually in the browser session. Resume execution after authentication.",
                screenshot=scr_auth,
            )
            application.status = ApplicationStatus.REQUIRES_USER_ACTION.value
            await db.commit()
            return snapshot

        # 7. Check for Security Challenges (CAPTCHA, Bot Check, OTP, 2FA)
        challenge_type, challenge_msg = await ChallengeDetector.detect_challenge(page)
        if challenge_type != ChallengeType.NONE:
            scr_chal = await ScreenshotManager.capture_checkpoint(
                page=page, step="challenge_detected", application_id=application_id
            )
            snapshot = self.execution_store.update_state(
                application_id=application_id,
                state=ExecutionStepState.USER_ACTION_REQUIRED,
                challenge_type=challenge_type,
                user_action_required=True,
                user_action_reason=challenge_type.value,
                user_instructions=challenge_msg or "Please complete the security challenge manually.",
                screenshot=scr_chal,
            )
            application.status = ApplicationStatus.REQUIRES_USER_ACTION.value
            await db.commit()
            return snapshot

        # 8. Inspect Form and Discovered Fields
        self.execution_store.update_state(
            application_id=application_id,
            state=ExecutionStepState.INSPECTING_FORM,
            current_step="form_inspection",
        )
        discovered_form = await FormParser.parse_form(page=page, form_id=f"form_{application_id}")

        scr_initial = await ScreenshotManager.capture_checkpoint(
            page=page, step="form_initial", application_id=application_id
        )
        self.execution_store.update_state(
            application_id=application_id,
            discovered_fields=discovered_form.fields,
            screenshot=scr_initial,
        )

        # 9. Synthesize Discovered Fields with Phase 6 Draft to build Execution Plan
        plan = FieldDetector.map_fields_to_plan(
            form=discovered_form,
            draft=draft,
            application_id=application_id,
        )
        self.execution_store.update_state(
            application_id=application_id,
            state=ExecutionStepState.FORM_READY,
            execution_plan=plan,
        )

        # 10. Execute Safe Actions
        self.execution_store.update_state(
            application_id=application_id,
            state=ExecutionStepState.FILLING,
            current_step="executing_safe_fields",
        )

        for action in plan.actions:
            if action.requires_user_input:
                continue

            try:
                if action.action_type == FieldActionType.UPLOAD_RESUME:
                    self.execution_store.update_state(
                        application_id=application_id,
                        state=ExecutionStepState.UPLOAD_IN_PROGRESS,
                    )
                    await ResumeUploader.upload_resume(
                        page=page,
                        db=db,
                        user_id=user_id,
                        resume_id=action.value,
                        selector=action.selector,
                    )
                    action.executed = True
                else:
                    await FieldExecutor.execute_action(page=page, action=action)
            except SubmissionBlockedError:
                raise
            except Exception as e:
                logger.warning("Field action failed for %s: %s", action.field_id, e)

        # Checkpoint: After Safe Filling
        scr_filled = await ScreenshotManager.capture_checkpoint(
            page=page, step="after_safe_fill", application_id=application_id
        )

        # 11. Finalize Execution State
        has_pending_user_input = any(a.requires_user_input for a in plan.actions)
        final_state = ExecutionStepState.READY_FOR_REVIEW if not has_pending_user_input else ExecutionStepState.USER_ACTION_REQUIRED

        snapshot = self.execution_store.update_state(
            application_id=application_id,
            state=final_state,
            user_action_required=has_pending_user_input,
            user_action_reason="UNRESOLVED_REQUIRED_FIELDS" if has_pending_user_input else None,
            user_instructions="Please complete unanswered or sensitive fields manually." if has_pending_user_input else None,
            execution_plan=plan,
            screenshot=scr_filled,
        )

        # 12. Update Database Application Status and Embed Screenshots
        if has_pending_user_input:
            application.status = ApplicationStatus.REQUIRES_USER_ACTION.value
        else:
            application.status = ApplicationStatus.PENDING_REVIEW.value

        # Append screenshots to review package
        review_pkg = dict(application.review_package or {})
        review_pkg["screenshots"] = [s.model_dump(mode="json") for s in snapshot.screenshots]
        application.review_package = review_pkg

        await db.commit()
        return snapshot

    async def resume_execution(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
        application_id: str,
    ) -> ExecutionStateSnapshot:
        """
        Resumes execution after a user completes a manual action (e.g. login, CAPTCHA, manual field).
        """
        # Verify ownership
        self.session_manager.get_session_record(session_id=session_id, user_id=user_id)

        # Re-run execution starting from current page state
        return await self.start_application_execution(
            db=db,
            user_id=user_id,
            application_id=application_id,
            session_id=session_id,
        )

    async def pause_execution(
        self,
        user_id: str,
        session_id: str,
        application_id: str,
    ) -> ExecutionStateSnapshot:
        """
        Explicitly pauses automated execution.
        """
        self.session_manager.get_session_record(session_id=session_id, user_id=user_id)
        snapshot = self.execution_store.update_state(
            application_id=application_id,
            state=ExecutionStepState.PAUSED_FOR_USER,
            user_action_required=True,
            user_action_reason="USER_PAUSED",
            user_instructions="Execution paused by user. Click Resume to continue.",
        )
        return snapshot
