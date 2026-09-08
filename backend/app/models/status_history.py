from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IDMixin, utc_now

if TYPE_CHECKING:
    from app.models.application import Application


class ApplicationStatusHistory(Base, IDMixin):
    """
    Append-only audit trail recording every state transition of an application.
    Tracks previous state, next state, actor (User/Agent/System), reason, and event metadata.
    """
    __tablename__ = "application_status_history"

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="SYSTEM", nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="status_history",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_status_history_app_created", "application_id", "created_at"),
    )
