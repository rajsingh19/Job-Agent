from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IDMixin, TimestampMixin, utc_now


class ApplicationApproval(Base, IDMixin, TimestampMixin):
    """
    Records an explicit, candidate-authorized human approval for an application draft version.
    Enforces the critical safety invariant: NO APPROVAL = NO SUBMISSION.
    """
    __tablename__ = "application_approvals"

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approved_version_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    approval_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    approval_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_approvals_app_version", "application_id", "approved_version_hash"),
    )
