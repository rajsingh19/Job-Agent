from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import ApplicationStatus, ConnectorType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.job import JobPosting
    from app.models.resume import Resume
    from app.models.status_history import ApplicationStatusHistory


class Application(Base, IDMixin, TimestampMixin):
    """
    Application entity tracking an end-to-end job application lifecycle.
    Enforces human-in-the-loop approval requirement before any submission attempt.
    """
    __tablename__ = "applications"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    connector: Mapped[str] = mapped_column(
        String(64),
        default=ConnectorType.GENERIC_BROWSER.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=ApplicationStatus.DISCOVERED.value,
        nullable=False,
        index=True,
    )
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Drafting & Review Content
    generated_answers: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    warnings: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    review_package: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Submission Tracking
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_response: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications", lazy="selectin")
    job: Mapped["JobPosting"] = relationship("JobPosting", back_populates="applications", lazy="selectin")
    resume: Mapped[Optional["Resume"]] = relationship("Resume", back_populates="applications", lazy="selectin")
    status_history: Mapped[List["ApplicationStatusHistory"]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.created_at",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_application"),
        Index("ix_applications_status_user", "status", "user_id"),
    )
