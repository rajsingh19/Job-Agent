import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.services.submission.approval_service import ApprovalService
from app.services.submission.audit_service import AuditService
from app.services.submission.exceptions import (
    AlreadySubmittedError,
    ApprovalExpiredError,
    ApprovalRequiredError,
    ConcurrentSubmissionError,
    SubmissionBlockedError,
    SubmissionConfirmationError,
    SubmissionControlNotFoundError,
    SubmissionError,
)
from app.services.submission.models import (
    ApprovalResponse,
    ApproveRequest,
    AuditEventResponse,
    RevokeApprovalRequest,
    SubmissionResponse,
    SubmitRequest,
)
from app.services.submission.submission_service import SubmissionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{application_id}/approve",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Explicit human approval for application submission",
)
async def approve_application_endpoint(
    application_id: str,
    request: ApproveRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Records explicit human approval for an application draft after verifying pre-submission rules.
    Binds the approval to a deterministic content version hash.
    """
    try:
        return await ApprovalService.record_approval(
            db=db,
            user_id=user_id,
            application_id=application_id,
            confirmation_checked=request.confirmation_checked,
            user_notes=request.user_notes,
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "APPLICATION_NOT_FOUND", "message": err_msg},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "APPROVAL_REJECTED", "message": err_msg},
        )
    except Exception as e:
        logger.exception("Unexpected error in approve_application: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_ERROR", "message": str(e)},
        )


@router.post(
    "/{application_id}/revoke-approval",
    status_code=status.HTTP_200_OK,
    summary="Revoke previously granted approval",
)
async def revoke_approval_endpoint(
    application_id: str,
    request: RevokeApprovalRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Revokes an active approval and reverts application status to PENDING_REVIEW.
    """
    try:
        success = await ApprovalService.revoke_approval(
            db=db,
            user_id=user_id,
            application_id=application_id,
            reason=request.reason,
        )
        return {"revoked": success, "application_id": application_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "APPLICATION_NOT_FOUND", "message": str(e)},
        )


@router.get(
    "/{application_id}/approval",
    response_model=ApprovalResponse,
    summary="Get active approval status",
)
async def get_approval_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves active approval details and content hash for an application.
    """
    approval = await ApprovalService.get_active_approval(
        db=db,
        user_id=user_id,
        application_id=application_id,
    )
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NO_ACTIVE_APPROVAL", "message": "No active approval exists for this application."},
        )

    return ApprovalResponse(
        application_id=application_id,
        status="APPROVED",
        approved=True,
        approved_at=approval.approved_at,
        approved_version_hash=approval.approved_version_hash,
        approval_token=approval.approval_token,
        ready_for_submission=True,
    )


@router.post(
    "/{application_id}/submit",
    response_model=SubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute final application submission",
)
async def submit_application_endpoint(
    application_id: str,
    request: SubmitRequest,
    session_id: Optional[str] = Query(None, description="Active browser session ID"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes the final application submission on the external portal.
    CRITICAL: Strictly blocked unless an active approval token matching the current draft exists.
    """
    try:
        return await SubmissionService.execute_submission(
            db=db,
            user_id=user_id,
            application_id=application_id,
            approval_token=request.approval_token,
            session_id=session_id,
        )
    except AlreadySubmittedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "ALREADY_SUBMITTED", "message": str(e)},
        )
    except ApprovalExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "APPROVAL_EXPIRED", "message": str(e)},
        )
    except ApprovalRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "APPROVAL_REQUIRED", "message": str(e)},
        )
    except ConcurrentSubmissionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONCURRENT_SUBMISSION", "message": str(e)},
        )
    except SubmissionControlNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "SUBMISSION_CONTROL_NOT_FOUND", "message": str(e)},
        )
    except SubmissionBlockedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "SUBMISSION_BLOCKED", "message": str(e)},
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NOT_FOUND", "message": err_msg},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_REQUEST", "message": err_msg},
        )
    except Exception as e:
        logger.exception("Unexpected error in submit_application: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "SUBMISSION_FAILED", "message": str(e)},
        )


@router.get(
    "/{application_id}/submission",
    summary="Get final submission status and response",
)
async def get_submission_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the portal response, confirmation ID, and submitted timestamps.
    """
    status_data = await SubmissionService.get_submission_status(
        db=db,
        user_id=user_id,
        application_id=application_id,
    )
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "APPLICATION_NOT_FOUND", "message": f"Application '{application_id}' not found."},
        )
    return status_data


@router.get(
    "/{application_id}/audit",
    response_model=List[AuditEventResponse],
    summary="Get immutable audit trail",
)
async def get_audit_trail_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the chronologically ordered immutable audit log for compliance inspection.
    """
    events = await AuditService.get_audit_trail(
        db=db,
        application_id=application_id,
        user_id=user_id,
    )
    return events

