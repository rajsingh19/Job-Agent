from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IDMixin, TimestampMixin, utc_now
from app.models.enums import ATSProvider, JobSourceType, RemoteType

if TYPE_CHECKING:
    from app.models.application import Application


class JobPosting(Base, IDMixin, TimestampMixin):
    """
    Normalized Job Posting entity discovered across API, ATS, and Browser sources.
    Includes deduplication hash and ATS provider detection metadata.
    """
    __tablename__ = "job_postings"

    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(32),
        default=JobSourceType.API.value,
        nullable=False,
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    company: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[str] = mapped_column(
        String(32),
        default=RemoteType.ANY.value,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Compensation & Level
    stipend_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stipend_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stipend_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    salary_interval: Mapped[Optional[str]] = mapped_column(String(20), default="month", nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # URLs and Providers
    apply_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    ats_provider: Mapped[str] = mapped_column(
        String(32),
        default=ATSProvider.UNKNOWN.value,
        nullable=False,
        index=True,
    )

    # Deduplication and Discovery Tracking
    source_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    raw_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_jobs_company_title", "company", "title"),
    )
