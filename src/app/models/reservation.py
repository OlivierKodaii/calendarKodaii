from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
import uuid

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    DateTime,
    Index,
    func,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.db.database import Base

if TYPE_CHECKING:
    from .slot import Slot
    from .user import User


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        # Index("ix_slot_host_id", "host_id"),
        # Index("ix_slot_status", "status"),
        Index("ix_slot_start_end_times", "slot_start_time", "slot_end_time"),
        Index("ix_reservation_deleted_at", "deleted_at"),
        CheckConstraint("slot_end_time > slot_start_time", name="valid_slot_duration"),
    )

    slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slots.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )

    # Time-related fields
    slot_start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    slot_end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    slot_duration: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Duration in minutes

    # Booking information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)

    # Metadata and versioning
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships - Using string annotations to avoid circular imports
    slot: Mapped["Slot"] = relationship("Slot", back_populates="reservations")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    host: Mapped["User"] = relationship("User", foreign_keys=[host_id])
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by]
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Status
    status: Mapped[str] = mapped_column(
        String, default="pending", nullable=False, index=True
    )  # pending, confirmed, cancelled
    version: Mapped[int] = mapped_column(Integer, default=1)  # For optimistic locking
