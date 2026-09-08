import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.schemas.application_draft import ApplicationDraft
from app.services.submission.approval_service import ApprovalService
from app.services.submission.approval_validator import ApprovalValidator
from app.services.submission.exceptions import (
    AlreadySubmittedError,
    ApprovalExpiredError,
    ApprovalRequiredError,
    ConcurrentSubmissionError,
)
from app.services.submission.models import SubmissionAuthorization

logger = logging.getLogger(__name__)


class SubmissionGuard:
    """
    CRITICAL SECURITY GUARD.
    Enforces the NO APPROVAL = NO SUBMISSION invariant.
    Validates ownership, state machine eligibility, approval tokens, content hash integrity,
    and prevents concurrent / duplicate submissions.
    """

    _active_submission_locks: Set[str] = set()
    _lock_mutex: asyncio.Lock = asyncio.Lock()

    @classmethod
    @asynccontextmanager
    async def submission_lock(cls, application_id: str):
        """
        Concurrency lock ensuring only one submission attempt runs per application.
        """
        async with cls._lock_mutex:
            if application_id in cls._active_submission_locks:
                raise ConcurrentSubmissionError(application_id)
            cls._active_submission_locks.add(application_id)

        try:
            yield
        finally:
            async with cls._lock_mutex:
                cls._active_submission_locks.discard(application_id)

    @classmethod
    async def authorize_submission(
        cls,
        db: AsyncSession,
        user_id: str,
        application_id: str,
        approval_token: Optional[str] = None,
    ) -> SubmissionAuthorization:
        """
        Validates all preconditions for submission and issues a sealed SubmissionAuthorization.
        
        Raises:
            AlreadySubmittedError: If already submitted.
            ApprovalRequiredError: If no active approval exists or status is not APPROVED.
            ApprovalExpiredError: If draft content changed since approval.
        """
        # 1. Fetch Application and check ownership
        stmt = select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
        res = await db.execute(stmt)
        application = res.scalars().first()
        if not application:
            raise ApprovalRequiredError(application_id, "Application not found or unauthorized.")

        # 2. Check duplicate / already submitted
        if application.status == ApplicationStatus.SUBMITTED.value:
            raise AlreadySubmittedError(
                application_id=application_id,
                submitted_at=str(application.submitted_at or ""),
            )

        # 3. Status must be APPROVED
        if application.status != ApplicationStatus.APPROVED.value:
            raise ApprovalRequiredError(
                application_id=application_id,
                message=f"Application status is '{application.status}'. Only APPROVED applications may be submitted.",
            )

        # 4. Check active approval record
        approval = await ApprovalService.get_active_approval(db, user_id, application_id)
        if not approval:
            raise ApprovalRequiredError(
                application_id=application_id,
                message="No active approval found for application.",
            )

        # 5. Check token match if token provided
        if approval_token and approval_token != approval.approval_token:
            raise ApprovalRequiredError(
                application_id=application_id,
                message="Approval token mismatch.",
            )

        # 6. Verify version hash integrity
        if not application.review_package or "fields" not in application.review_package:
            raise ApprovalRequiredError(
                application_id=application_id,
                message="Application has no review package to verify.",
            )

        draft = ApplicationDraft(**application.review_package)
        current_hash = ApprovalValidator.calculate_review_version_hash(draft=draft)

        if current_hash != approval.approved_version_hash:
            logger.warning(
                f"Version hash mismatch for application '{application_id}'. "
                f"Approved: {approval.approved_version_hash}, Current: {current_hash}"
            )
            raise ApprovalExpiredError(
                application_id=application_id,
                message="Application content was modified after approval was granted.",
            )

        # 7. Issue authorization token
        return SubmissionAuthorization(
            application_id=application_id,
            user_id=user_id,
            approved_version_hash=approval.approved_version_hash,
            approved_at=approval.approved_at,
            token=approval.approval_token,
        )
