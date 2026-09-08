import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.application import Application
from app.models.approval import ApplicationApproval
from app.models.enums import ApplicationStatus
from app.models.status_history import ApplicationStatusHistory
from app.schemas.application_draft import ApplicationDraft
from app.schemas.state_machine import ApplicationStateMachine
from app.services.submission.approval_validator import ApprovalValidator
from app.services.submission.audit_service import AuditService
from app.services.submission.models import ApprovalResponse

logger = logging.getLogger(__name__)


class ApprovalService:
    """
    Manages explicit candidate approvals with version hashing and invalidation.
    Guarantees that no application transitions to APPROVED without pre-submission validation.
    """

    @classmethod
    async def record_approval(
        cls,
        db: AsyncSession,
        user_id: str,
        application_id: str,
        confirmation_checked: bool,
        user_notes: Optional[str] = None,
    ) -> ApprovalResponse:
        """
        Processes candidate approval for an application.
        Validates draft readiness, computes content version hash, and stores approval record.
        """
        if not confirmation_checked:
            raise ValueError("Explicit candidate confirmation checkbox must be checked to approve.")

        # 1. Fetch Application and verify ownership
        stmt = select(Application).where(Application.id == application_id, Application.user_id == user_id)
        result = await db.execute(stmt)
        application = result.scalars().first()
        if not application:
            raise ValueError(f"Application '{application_id}' not found or unauthorized.")

        # 2. Verify draft content exists
        if not application.review_package or "fields" not in application.review_package:
            raise ValueError(f"Application '{application_id}' has no valid draft to approve.")

        draft = ApplicationDraft(**application.review_package)

        # 3. Pre-submission validation
        is_valid, errors = ApprovalValidator.validate_for_approval(draft=draft)
        if not is_valid:
            await AuditService.log_event(
                db=db,
                application_id=application_id,
                user_id=user_id,
                event_type="VALIDATION_FAILED",
                details={"errors": errors},
            )
            raise ValueError(f"Pre-submission validation failed: {'; '.join(errors)}")

        await AuditService.log_event(
            db=db,
            application_id=application_id,
            user_id=user_id,
            event_type="VALIDATION_PASSED",
        )

        # 4. Compute deterministic content version hash
        version_hash = ApprovalValidator.calculate_review_version_hash(draft=draft)

        # 5. Revoke any prior approvals for this application
        await db.execute(
            update(ApplicationApproval)
            .where(
                ApplicationApproval.application_id == application_id,
                ApplicationApproval.is_approved == True,
            )
            .values(is_approved=False, is_revoked=True, revoked_reason="Superseded by new approval")
        )

        # 6. Create new ApplicationApproval record
        approval_token = f"appr_{uuid.uuid4().hex}"
        approval = ApplicationApproval(
            id=f"appr_rec_{uuid.uuid4().hex[:12]}",
            application_id=application_id,
            user_id=user_id,
            approved_version_hash=version_hash,
            approval_token=approval_token,
            is_approved=True,
            is_revoked=False,
            approved_at=datetime.now(timezone.utc),
            approval_metadata={"notes": user_notes} if user_notes else {},
        )
        db.add(approval)

        # 7. Transition Application state to APPROVED
        old_status = application.status
        new_status = ApplicationStatus.APPROVED.value

        # Enforce state machine transition
        ApplicationStateMachine.validate_transition(old_status, new_status, reason="Candidate explicit approval")
        application.status = new_status

        # 8. Add Status History
        history = ApplicationStatusHistory(
            id=f"hist_{uuid.uuid4().hex[:12]}",
            application_id=application_id,
            from_status=old_status,
            to_status=new_status,
            actor="USER",
            reason="Candidate explicitly approved application for submission",
            event_metadata={"version_hash": version_hash, "approval_token": approval_token},
        )
        db.add(history)

        # 9. Audit event
        await AuditService.log_event(
            db=db,
            application_id=application_id,
            user_id=user_id,
            event_type="APPROVED",
            version_hash=version_hash,
            details={"approval_token": approval_token, "notes": user_notes},
        )

        await db.commit()

        return ApprovalResponse(
            application_id=application_id,
            status=new_status,
            approved=True,
            approved_at=approval.approved_at,
            approved_version_hash=version_hash,
            approval_token=approval_token,
            ready_for_submission=True,
        )

    @classmethod
    async def revoke_approval(
        cls,
        db: AsyncSession,
        user_id: str,
        application_id: str,
        reason: str = "User requested revision",
    ) -> bool:
        """
        Revokes an existing approval and resets application status to PENDING_REVIEW.
        """
        stmt = select(Application).where(Application.id == application_id, Application.user_id == user_id)
        res = await db.execute(stmt)
        application = res.scalars().first()
        if not application:
            raise ValueError(f"Application '{application_id}' not found.")

        # Revoke approvals
        await db.execute(
            update(ApplicationApproval)
            .where(
                ApplicationApproval.application_id == application_id,
                ApplicationApproval.is_approved == True,
            )
            .values(is_approved=False, is_revoked=True, revoked_reason=reason)
        )

        # Reset status if currently APPROVED
        if application.status == ApplicationStatus.APPROVED.value:
            old_status = application.status
            new_status = ApplicationStatus.PENDING_REVIEW.value
            application.status = new_status

            history = ApplicationStatusHistory(
                id=f"hist_{uuid.uuid4().hex[:12]}",
                application_id=application_id,
                from_status=old_status,
                to_status=new_status,
                actor="USER",
                reason=f"Approval revoked: {reason}",
            )
            db.add(history)

        await AuditService.log_event(
            db=db,
            application_id=application_id,
            user_id=user_id,
            event_type="APPROVAL_REVOKED",
            details={"reason": reason},
        )

        await db.commit()
        return True

    @classmethod
    async def get_active_approval(
        cls,
        db: AsyncSession,
        user_id: str,
        application_id: str,
    ) -> Optional[ApplicationApproval]:
        """
        Retrieves active, non-revoked approval for an application.
        """
        stmt = (
            select(ApplicationApproval)
            .where(
                ApplicationApproval.application_id == application_id,
                ApplicationApproval.user_id == user_id,
                ApplicationApproval.is_approved == True,
                ApplicationApproval.is_revoked == False,
            )
            .order_by(ApplicationApproval.approved_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()
