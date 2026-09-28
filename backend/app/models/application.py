from __future__ import annotations

import uuid

from sqlalchemy import ARRAY, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ApplicationEnvironment, ApplicationStatus


class Application(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    environment: Mapped[ApplicationEnvironment] = mapped_column(
        String(30), default=ApplicationEnvironment.PRODUCTION.value, nullable=False
    )
    owning_team: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    support_contact: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        String(30), default=ApplicationStatus.ACTIVE.value, nullable=False
    )
    features: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    modules: Mapped[list["ApplicationModule"]] = relationship(
        "ApplicationModule", back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationModule(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "application_modules"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    features: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    application: Mapped["Application"] = relationship("Application", back_populates="modules")
