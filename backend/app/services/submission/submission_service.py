import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.status_history import ApplicationStatusHistory
from app.schemas.state_machine import ApplicationStateMachine
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.session_manager import SessionManager
from app.services.submission.audit_service import AuditService
from app.services.submission.browser_submitter import BrowserSubmitter
from app.services.submission.exceptions import (
    AlreadySubmittedError,
    ApprovalRequiredError,
    SubmissionConfirmationError,
)
from app.services.submission.models import (
    ConfirmationStatus,
    SubmissionResponse,
    SubmissionResult,
)
from app.services.submission.submission_guard import SubmissionGuard

logger = logging.getLogger(__name__)


class SubmissionService:
    """
    Master orchestrator for Phase 8 application submission.
    Coordinates SubmissionGuard validation, state machine transitions,
    browser submission execution, confirmation detection, and compliance auditing.
    """

    @classmethod
    async def execute_submission(
        cls,
        db: AsyncSession,
        user_id: str,
        application_id: str,
        approval_token: Optional[str] = None,
        session_id: Optional[str] = None,
        page: Optional[Any] = None,
    ) -> SubmissionResponse:
        """
        Executes final application submission under strict human-in-the-loop controls.
        """
        # 1. Concurrency lock to prevent race conditions
        async with SubmissionGuard.submission_lock(application_id):
            # 2. Fetch Application and check current state
            stmt = select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id,
            )
            res = await db.execute(stmt)
            application = res.scalars().first()
            if not application:
                raise ApprovalRequiredError(application_id, "Application not found or unauthorized.")

            # Idempotency check: Reject duplicate submissions
            if application.status == ApplicationStatus.SUBMITTED.value:
                raise AlreadySubmittedError(
                    application_id=application_id,
                    submitted_at=str(application.submitted_at or ""),
                )

            # 3. Authorize submission via SubmissionGuard (validates hash, approval token, status)
            authorization = await SubmissionGuard.authorize_submission(
                db=db,
                user_id=user_id,
                application_id=application_id,
                approval_token=approval_token,
            )

            # 4. State transition: APPROVED -> SUBMITTING
            old_status = application.status
            new_status = ApplicationStatus.SUBMITTING.value
            ApplicationStateMachine.validate_transition(
                old_status, new_status, reason="Final submission initiated"
            )
            application.status = new_status

            db.add(
                ApplicationStatusHistory(
                    id=f"hist_{uuid.uuid4().hex[:12]}",
                    application_id=application_id,
                    from_status=old_status,
                    to_status=new_status,
                    actor="USER",
                    reason="Submission execution started",
                    event_metadata={"token": authorization.token},
                )
            )

            await AuditService.log_event(
                db=db,
                application_id=application_id,
                user_id=user_id,
                event_type="SUBMISSION_INITIATED",
                version_hash=authorization.approved_version_hash,
                details={"token": authorization.token},
            )

            # Commit the transition to SUBMITTING before executing browser click
            await db.commit()

            # 5. Resolve Playwright page
            target_page = page
            if not target_page and session_id:
                session_mgr = SessionManager.get_instance()
                # Verify session ownership
                session_mgr.get_session_record(session_id=session_id, user_id=user_id)
                bm = await BrowserManager.get_instance()
                sess_ctx = bm.get_session(session_id)
                if sess_ctx:
                    target_page = sess_ctx.page

            if not target_page:
                raise ValueError(
                    "Cannot execute browser submission: No active browser page or session provided."
                )

            # 6. Execute submission via BrowserSubmitter
            try:
                result: SubmissionResult = await BrowserSubmitter.submit(
                    page=target_page,
                    authorization=authorization,
                    application_id=application_id,
                )
            except Exception as exc:
                logger.error(f"Error during submission execution for {application_id}: {exc}")
                # Reset or fail application
                application.status = ApplicationStatus.FAILED.value
                db.add(
                    ApplicationStatusHistory(
                        id=f"hist_{uuid.uuid4().hex[:12]}",
                        application_id=application_id,
                        from_status=ApplicationStatus.SUBMITTING.value,
                        to_status=ApplicationStatus.FAILED.value,
                        actor="SYSTEM",
                        reason=f"Submission execution failed: {str(exc)}",
                    )
                )
                await AuditService.log_event(
                    db=db,
                    application_id=application_id,
                    user_id=user_id,
                    event_type="SUBMISSION_FAILED",
                    details={"error": str(exc)},
                )
                await db.commit()
                raise

            # 7. Evaluate Confirmation Outcome
            if result.status == ConfirmationStatus.CONFIRMED:
                post_status = ApplicationStatus.SUBMITTED.value
                application.status = post_status
                application.submitted_at = result.submitted_at
                application.submission_response = result.model_dump(mode="json")

                db.add(
                    ApplicationStatusHistory(
                        id=f"hist_{uuid.uuid4().hex[:12]}",
                        application_id=application_id,
                        from_status=ApplicationStatus.SUBMITTING.value,
                        to_status=post_status,
                        actor="SYSTEM",
                        reason="Submission confirmed by portal",
                        event_metadata={
                            "confirmation_type": result.confirmation_type,
                            "confirmation_reference": result.confirmation_reference,
                        },
                    )
                )

                await AuditService.log_event(
                    db=db,
                    application_id=application_id,
                    user_id=user_id,
                    event_type="SUBMISSION_CONFIRMED",
                    version_hash=authorization.approved_version_hash,
                    details={
                        "confirmation_type": result.confirmation_type,
                        "confirmation_reference": result.confirmation_reference,
                        "confirmation_url": result.confirmation_url,
                    },
                )

            elif result.status == ConfirmationStatus.UNKNOWN:
                post_status = ApplicationStatus.REQUIRES_USER_ACTION.value
                application.status = post_status
                application.submission_response = result.model_dump(mode="json")

                db.add(
                    ApplicationStatusHistory(
                        id=f"hist_{uuid.uuid4().hex[:12]}",
                        application_id=application_id,
                        from_status=ApplicationStatus.SUBMITTING.value,
                        to_status=post_status,
                        actor="SYSTEM",
                        reason="Submission completed but confirmation is ambiguous. User verification required.",
                        event_metadata={"warnings": result.warnings},
                    )
                )

                await AuditService.log_event(
                    db=db,
                    application_id=application_id,
                    user_id=user_id,
                    event_type="SUBMISSION_AMBIGUOUS",
                    version_hash=authorization.approved_version_hash,
                    details={"warnings": result.warnings},
                )

            else:  # NOT_CONFIRMED
                post_status = ApplicationStatus.FAILED.value
                application.status = post_status
                application.submission_response = result.model_dump(mode="json")

                db.add(
                    ApplicationStatusHistory(
                        id=f"hist_{uuid.uuid4().hex[:12]}",
                        application_id=application_id,
                        from_status=ApplicationStatus.SUBMITTING.value,
                        to_status=post_status,
                        actor="SYSTEM",
                        reason="Portal rejected or indicated errors during submission.",
                        event_metadata={"warnings": result.warnings},
                    )
                )

                await AuditService.log_event(
                    db=db,
                    application_id=application_id,
                    user_id=user_id,
                    event_type="SUBMISSION_REJECTED",
                    version_hash=authorization.approved_version_hash,
                    details={"warnings": result.warnings},
                )

            await db.commit()

            return SubmissionResponse(
                application_id=application_id,
                status=application.status,
                submitted_at=result.submitted_at,
                confirmation_type=result.confirmation_type,
                confirmation_reference=result.confirmation_reference,
                confirmation_url=result.confirmation_url,
                warnings=result.warnings,
            )

    @classmethod
    async def get_submission_status(
        cls,
        db: AsyncSession,
        user_id: str,
        application_id: str,
    ) -> Optional[dict]:
        """
        Returns latest submission response details for an application.
        """
        stmt = select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
        res = await db.execute(stmt)
        application = res.scalars().first()
        if not application:
            return None

        return {
            "application_id": application.id,
            "status": application.status,
            "submitted_at": application.submitted_at,
            "submission_response": application.submission_response,
        }
