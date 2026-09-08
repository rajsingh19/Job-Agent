import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user_id
from app.database.session import get_db
from app.models.application import Application
from app.services.browser.execution_service import BrowserExecutionService
from app.services.browser.execution_state import ApplicationExecutionStore
from app.services.browser.models import ExecutionStateSnapshot
from app.services.portal.models import PortalCapabilities, PortalConfig, PortalDiagnostics
from app.services.portal.registry import PortalRegistry

logger = logging.getLogger(__name__)

router = APIRouter()
registry = PortalRegistry.get_instance()
execution_store = ApplicationExecutionStore.get_instance()
execution_service = BrowserExecutionService()


@router.get(
    "/portals",
    summary="List all supported ATS and job portals",
    response_model=Dict[str, PortalCapabilities],
)
async def list_portals_endpoint():
    """
    Returns the capability matrix for all supported ATS / job portal connectors.
    """
    return registry.list_all_capabilities()


@router.get(
    "/portals/{portal_id}",
    summary="Get configuration and capabilities for a specific portal",
)
async def get_portal_details_endpoint(portal_id: str):
    """
    Retrieves capabilities and declarative configuration for a specific portal.
    """
    adapter = registry.get_adapter(portal_id)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "PORTAL_NOT_FOUND", "message": f"Portal '{portal_id}' is not supported."},
        )

    return {
        "portal_id": adapter.portal_id,
        "name": adapter.name,
        "capabilities": adapter.capabilities().model_dump(mode="json"),
        "config": adapter.get_config().model_dump(mode="json"),
    }


@router.get(
    "/applications/{application_id}/portal-diagnostics",
    summary="Get execution diagnostics for an application",
    response_model=Optional[Dict[str, Any]],
)
async def get_application_portal_diagnostics_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns sanitized portal diagnostics for the application.
    Enforces multi-tenant authorization. Secrets and credentials are NEVER returned.
    """
    # Verify ownership
    stmt = select(Application).where(Application.id == application_id, Application.user_id == user_id)
    res = await db.execute(stmt)
    application = res.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "APPLICATION_NOT_FOUND", "message": f"Application '{application_id}' not found."},
        )

    # 1. Check in-memory store
    snapshot = execution_store.get_snapshot(application_id)
    if snapshot and snapshot.portal_diagnostics:
        return snapshot.portal_diagnostics

    # 2. Check persisted review package
    if application.review_package and "portal_diagnostics" in application.review_package:
        return application.review_package["portal_diagnostics"]

    # 3. Fallback placeholder
    return {
        "portal_id": "generic_ats",
        "portal_name": "Generic ATS",
        "url_domain": "",
        "current_step": {"step_index": 1, "has_next": False, "has_submit": False, "is_final_step": False},
        "total_fields_discovered": 0,
        "missing_required_fields": [],
        "auth_state": "UNKNOWN",
        "challenge_state": "NONE",
        "selector_failures": [],
        "navigation_history": [],
        "timeline": [],
        "warnings": ["No active portal diagnostics captured yet."],
    }


@router.post(
    "/applications/{application_id}/execution/resume",
    response_model=ExecutionStateSnapshot,
    summary="Resume execution for an application",
)
async def resume_application_execution_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Resumes browser execution for the application after manual user resolution.
    """
    stmt = select(Application).where(Application.id == application_id, Application.user_id == user_id)
    res = await db.execute(stmt)
    application = res.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "APPLICATION_NOT_FOUND", "message": f"Application '{application_id}' not found."},
        )

    snapshot = execution_store.get_snapshot(application_id)
    session_id = snapshot.session_id if snapshot else None

    return await execution_service.start_application_execution(
        db=db,
        user_id=user_id,
        application_id=application_id,
        session_id=session_id,
    )


@router.post(
    "/applications/{application_id}/execution/pause",
    response_model=ExecutionStateSnapshot,
    summary="Pause execution for an application",
)
async def pause_application_execution_endpoint(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Pauses browser execution for the application.
    """
    stmt = select(Application).where(Application.id == application_id, Application.user_id == user_id)
    res = await db.execute(stmt)
    application = res.scalars().first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "APPLICATION_NOT_FOUND", "message": f"Application '{application_id}' not found."},
        )

    snapshot = execution_store.get_snapshot(application_id)
    session_id = snapshot.session_id if snapshot else "unknown"

    return await execution_service.pause_execution(
        user_id=user_id,
        session_id=session_id,
        application_id=application_id,
    )
