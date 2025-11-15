from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.db.database import Base

if TYPE_CHECKING:
    from .reservation import Reservation
    from .user import User


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        Index("ix_slot_host_id", "host_id"),
        Index("ix_slot_status", "status"),
    )

    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    status: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships - Using string annotations to avoid circular imports
    host: Mapped["User"] = relationship("User", back_populates="hosted_slots")
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation", back_populates="slot", cascade="all, delete-orphan"
    )
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
