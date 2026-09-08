from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ApplicationStatus


class StatusHistoryBase(BaseModel):
    application_id: str
    from_status: Optional[ApplicationStatus] = None
    to_status: ApplicationStatus
    actor: str = "SYSTEM"
    reason: Optional[str] = None
    event_metadata: Dict[str, Any] = Field(default_factory=dict)


class StatusHistoryCreate(StatusHistoryBase):
    pass


class StatusHistoryResponse(StatusHistoryBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
