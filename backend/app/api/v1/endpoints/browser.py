import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.services.browser.browser_manager import BrowserManager
from app.services.browser.enums import BrowserSessionStatus
from app.services.browser.exceptions import (
    BrowserAuthenticationRequiredError,
    BrowserChallengeDetectedError,
    BrowserExecutionError,
    BrowserSessionNotFoundError,
    SubmissionBlockedError,
    UserActionRequiredError,
)
from app.services.browser.execution_service import BrowserExecutionService
from app.services.browser.execution_state import ApplicationExecutionStore
from app.services.browser.form_parser import FormParser
from app.services.browser.models import (
    BrowserField,
    BrowserSessionInfo,
    DiscoveredForm,
    ExecutionStateSnapshot,
    ScreenshotMetadata,
)
from app.services.browser.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()
execution_service = BrowserExecutionService()
session_manager = SessionManager.get_instance()
execution_store = ApplicationExecutionStore.get_instance()


class StartExecutionRequest(BaseModel):
    session_id: Optional[str] = None


class ResumeExecutionRequest(BaseModel):
    application_id: str


class PauseExecutionRequest(BaseModel):
    application_id: str


@router.post(
    "/sessions",
    response_model=BrowserSessionInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new browser session",
)
async def create_browser_session_endpoint(
    user_id: str = Depends(get_current_user_id),
):
    """
    Creates an isolated browser session context for the authenticated user.
    Never exposes internal cookies, tokens, or storage states.
    """
    try:
        return await session_manager.create_session(user_id=user_id)
    except Exception as e:
        logger.error("Failed to create browser session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "SESSION_CREATION_FAILED", "message": str(e)},
        )


@router.get(
    "/sessions/{session_id}",
    response_model=BrowserSessionInfo,
    summary="Get browser session metadata",
)
async def get_browser_session_endpoint(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Retrieves safe metadata for an active browser session.
    Validates user ownership and returns 404 if unauthorized or expired.
    """
    try:
        record = session_manager.get_session_record(session_id=session_id, user_id=user_id)
        return record.to_info()
    except BrowserSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": str(e)},
        )


@router.post(
    "/applications/{application_id}/start",
    response_model=ExecutionStateSnapshot,
    summary="Start automated browser application preparation",
)
async def start_application_execution_endpoint(
    application_id: str,
    request: StartExecutionRequest = StartExecutionRequest(),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Starts automated browser preparation for an application.
    Executes safe field filling and resume upload.
    STRICTLY blocked from final submission.
    """
    try:
        return await execution_service.start_application_execution(
            db=db,
            user_id=user_id,
            application_id=application_id,
            session_id=request.session_id,
        )
    except SubmissionBlockedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "SUBMISSION_BLOCKED", "message": str(e)},
        )
    except BrowserExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BROWSER_EXECUTION_ERROR", "message": str(e)},
        )
    except Exception as e:
        logger.error("Unexpected execution error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "EXECUTION_INTERNAL_ERROR", "message": str(e)},
        )


@router.get(
    "/sessions/{session_id}/form",
    response_model=DiscoveredForm,
    summary="Inspect form fields on current page",
)
async def inspect_session_form_endpoint(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Inspects and parses the visible application form on the active page of the session.
    """
    session_manager.get_session_record(session_id=session_id, user_id=user_id)
    bm = await BrowserManager.get_instance()
    sess_ctx = bm.get_session(session_id)
    if not sess_ctx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session context not found."},
        )

    return await FormParser.parse_form(page=sess_ctx.page, form_id=f"inspect_{session_id}")


@router.post(
    "/sessions/{session_id}/resume",
    response_model=ExecutionStateSnapshot,
    summary="Resume execution after user manual action",
)
async def resume_session_execution_endpoint(
    session_id: str,
    request: ResumeExecutionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Resumes browser automation after the user resolves a challenge (login, CAPTCHA, manual fields).
    """
    try:
        return await execution_service.resume_execution(
            db=db,
            user_id=user_id,
            session_id=session_id,
            application_id=request.application_id,
        )
    except BrowserSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "RESUME_FAILED", "message": str(e)},
        )


@router.post(
    "/sessions/{session_id}/pause",
    response_model=ExecutionStateSnapshot,
    summary="Pause active browser execution",
)
async def pause_session_execution_endpoint(
    session_id: str,
    request: PauseExecutionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Explicitly pauses browser automation.
    """
    try:
        return await execution_service.pause_execution(
            user_id=user_id,
            session_id=session_id,
            application_id=request.application_id,
        )
    except BrowserSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": str(e)},
        )


@router.get(
    "/applications/{application_id}/execution",
    response_model=ExecutionStateSnapshot,
    summary="Get application browser execution snapshot",
)
async def get_execution_snapshot_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Retrieves the current execution state snapshot for an application.
    """
    snapshot = execution_store.get_snapshot(application_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "EXECUTION_NOT_FOUND", "message": f"No active execution state found for application '{application_id}'."},
        )
    return snapshot


@router.get(
    "/applications/{application_id}/screenshots",
    response_model=List[ScreenshotMetadata],
    summary="Get screenshots captured during execution",
)
async def get_application_screenshots_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Returns safe metadata for all screenshots captured during execution.
    """
    snapshot = execution_store.get_snapshot(application_id)
    if not snapshot:
        return []
    return snapshot.screenshots
