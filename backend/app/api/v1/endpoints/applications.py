from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.schemas.application_draft import (
    ApplicationDraft,
    ApplicationDraftValidationResponse,
    ApplicationReviewPackageResponse,
)
from app.services.applications.draft_service import ApplicationDraftService

router = APIRouter()
draft_service = ApplicationDraftService()


@router.get(
    "/{application_id}/draft",
    response_model=ApplicationDraft,
    summary="Get application draft details",
)
async def get_application_draft_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves an existing application draft for the authenticated user."""
    try:
        return await draft_service.get_draft(
            db=db,
            user_id=user_id,
            application_id=application_id,
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
            detail={"error": "DRAFT_RETRIEVAL_FAILED", "message": err_msg},
        )


@router.post(
    "/{application_id}/validate",
    response_model=ApplicationDraftValidationResponse,
    summary="Validate an application draft",
)
async def validate_application_draft_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Validates required fields, format compliance, and truthfulness of a draft."""
    try:
        return await draft_service.validate_draft(
            db=db,
            user_id=user_id,
            application_id=application_id,
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
            detail={"error": "VALIDATION_FAILED", "message": err_msg},
        )


@router.get(
    "/{application_id}/review",
    response_model=ApplicationReviewPackageResponse,
    summary="Get complete human-in-the-loop application review package",
)
async def get_application_review_package_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the consolidated review package presented to the user for explicit
    human approval before any submission attempt.
    """
    try:
        return await draft_service.get_review_package(
            db=db,
            user_id=user_id,
            application_id=application_id,
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
            detail={"error": "REVIEW_PACKAGE_FAILED", "message": err_msg},
        )
