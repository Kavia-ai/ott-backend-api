from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    """Create timezone-aware timestamps for persisted records."""
    return datetime.now(timezone.utc)


class User(Base):
    """Account identity and credential record."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    display_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Subscription(Base):
    """A selected paid plan or free-trial enrollment for one user."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    plan_slug: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship(back_populates="subscriptions")
