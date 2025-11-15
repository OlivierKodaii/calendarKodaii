from enum import Enum, auto


class SlotStatusEnum(str, Enum):
    """Enum for slot status."""

    AVAILABLE = "available"
    RESERVED = "reserved"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    PENDING = "pending"
    BLOCKED = "blocked"


class ReservationStatusEnum(str, Enum):
    """Enum for reservation status."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
