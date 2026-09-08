from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import Settings, get_settings
from app.database.session import get_db

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """
    Health check endpoint returning application status, environment, and database connectivity.
    """
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "database": db_status,
        "human_in_the_loop_enforced": settings.require_explicit_approval,
    }
