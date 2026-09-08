from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IDMixin, utc_now

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.profile import UserPreference
    from app.models.application import Application


class User(Base, IDMixin):
    """
    User entity representing a candidate using the Job Application Agent.
    """
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    resumes: Mapped[List["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Resume.created_at)",
        lazy="selectin",
    )
    preference: Mapped[Optional["UserPreference"]] = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Application.created_at)",
        lazy="selectin",
    )
