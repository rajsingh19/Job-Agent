import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import ApplicationAuditEvent
from app.services.submission.models import AuditEventResponse

logger = logging.getLogger(__name__)

# Keys that must never be recorded in audit details
SENSITIVE_AUDIT_KEYS = {"password", "token", "cookie", "storage_state", "authorization"}


class AuditService:
    """
    Manages an append-only audit trail for all approval and submission lifecycle events.
    Enforces secret redaction and tenant isolation.
    """

    @classmethod
    async def log_event(
        cls,
        db: AsyncSession,
        application_id: str,
        user_id: str,
        event_type: str,
        version_hash: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ApplicationAuditEvent:
        """
        Creates and persists an immutable audit event.
        """
        safe_details = {}
        if details:
            for k, v in details.items():
                if any(s in k.lower() for s in SENSITIVE_AUDIT_KEYS):
                    safe_details[k] = "[REDACTED]"
                else:
                    safe_details[k] = v

        event = ApplicationAuditEvent(
            id=f"audit_{uuid.uuid4().hex[:12]}",
            application_id=application_id,
            user_id=user_id,
            event_type=event_type,
            version_hash=version_hash,
            details=safe_details,
        )
        db.add(event)
        await db.flush()
        logger.info("Audit logged: %s for application: %s", event_type, application_id)
        return event

    @classmethod
    async def get_audit_trail(
        cls,
        db: AsyncSession,
        application_id: str,
        user_id: str,
    ) -> List[AuditEventResponse]:
        """
        Retrieves the complete audit trail for an application, validating user ownership.
        """
        stmt = (
            select(ApplicationAuditEvent)
            .where(
                ApplicationAuditEvent.application_id == application_id,
                ApplicationAuditEvent.user_id == user_id,
            )
            .order_by(ApplicationAuditEvent.created_at.asc())
        )
        res = await db.execute(stmt)
        events = res.scalars().all()

        return [
            AuditEventResponse(
                id=e.id,
                application_id=e.application_id,
                event_type=e.event_type,
                version_hash=e.version_hash,
                details=e.details,
                created_at=e.created_at,
            )
            for e in events
        ]
