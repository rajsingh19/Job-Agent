from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.application import Application


class Resume(Base, IDMixin, TimestampMixin):
    """
    Resume model storing uploaded candidate resumes, content hashes, and structured parsed profile data.
    """
    __tablename__ = "resumes"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parsed_profile: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes", lazy="selectin")
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="resume",
        lazy="selectin",
    )
