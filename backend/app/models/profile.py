from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IDMixin, TimestampMixin
from app.models.enums import RemoteType, ExperienceLevel

if TYPE_CHECKING:
    from app.models.user import User


class UserPreference(Base, IDMixin, TimestampMixin):
    """
    Explicit user preferences that configure the job discovery and matching engine.
    Separated strictly from parsed ResumeProfile so LLM parsing never overwrites user constraints.
    """
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    target_roles: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_locations: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    remote_preference: Mapped[str] = mapped_column(
        String(32),
        default=RemoteType.ANY.value,
        nullable=False,
    )
    minimum_stipend: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    maximum_stipend: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stipend_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    experience_level: Mapped[Optional[str]] = mapped_column(
        String(32),
        default=ExperienceLevel.ENTRY_LEVEL.value,
        nullable=True,
    )
    required_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    excluded_companies: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_company_types: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    additional_preferences: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preference", lazy="selectin")
