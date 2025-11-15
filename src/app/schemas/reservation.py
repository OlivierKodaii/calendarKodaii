from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, validator

from .enums import ReservationStatusEnum


class ReservationBase(BaseModel):
    """Base Reservation model with core fields."""

    slot_id: Annotated[UUID, Field(..., description="Reference to the booked slot")]
    host_id: Annotated[UUID, Field(..., description="Reference to the host user")]
    guest_name: Annotated[
        str, Field(..., min_length=1, max_length=100, description="Guest's full name")
    ]
    guest_email: Annotated[
        EmailStr, Field(..., description="Guest's email address for notifications")
    ]
    subject: Annotated[
        str,
        Field(
            ..., min_length=1, max_length=200, description="Meeting subject or purpose"
        ),
    ]

    @validator("guest_email")
    def validate_guest_email(cls, v):
        if not v:
            raise ValueError("Guest email is required")
        return v.lower()

    @validator("guest_name")
    def validate_guest_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Guest name cannot be empty")
        return v.strip()

    @validator("subject")
    def validate_subject(cls, v):
        if not v or not v.strip():
            raise ValueError("Subject cannot be empty")
        return v.strip()


class Reservation(ReservationBase):
    """Complete Reservation model."""

    status: Annotated[
        ReservationStatusEnum,
        Field(
            default=ReservationStatusEnum.PENDING,
            description="Current reservation status",
        ),
    ]
    created_at: Annotated[
        datetime,
        Field(default_factory=datetime.utcnow, description="Creation timestamp"),
    ]
    updated_at: Annotated[
        Optional[datetime], Field(default=None, description="Last update timestamp")
    ]

    class Config:
        from_attributes = True


class ReservationRead(BaseModel):
    """Schema for reading reservation data."""

    id: UUID
    slot_id: UUID
    host_id: UUID
    guest_name: str
    guest_email: EmailStr
    subject: str
    status: ReservationStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReservationCreate(ReservationBase):
    """Schema for creating reservations."""

    model_config = ConfigDict(extra="forbid")


class ReservationCreateInternal(ReservationBase):
    """Schema for internal reservation creation."""

    status: Annotated[
        ReservationStatusEnum,
        Field(
            default=ReservationStatusEnum.PENDING,
            description="Current reservation status",
        ),
    ]


class ReservationUpdate(BaseModel):
    """Schema for updating reservations."""

    model_config = ConfigDict(extra="forbid")

    guest_name: Annotated[
        Optional[str],
        Field(
            default=None, min_length=1, max_length=100, description="Guest's full name"
        ),
    ]
    guest_email: Annotated[
        Optional[EmailStr],
        Field(default=None, description="Guest's email address for notifications"),
    ]
    subject: Annotated[
        Optional[str],
        Field(
            default=None,
            min_length=1,
            max_length=200,
            description="Meeting subject or purpose",
        ),
    ]
    status: Annotated[
        Optional[ReservationStatusEnum],
        Field(default=None, description="Current reservation status"),
    ]

    @validator("guest_name")
    def validate_guest_name(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError("Guest name cannot be empty")
            return v.strip()
        return v

    @validator("guest_email")
    def validate_guest_email(cls, v):
        if v is not None:
            return v.lower()
        return v

    @validator("subject")
    def validate_subject(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError("Subject cannot be empty")
            return v.strip()
        return v


class ReservationUpdateInternal(ReservationUpdate):
    """Schema for internal reservation updates."""

    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReservationStatusUpdate(BaseModel):
    """Schema for specifically updating just the reservation status."""

    status: ReservationStatusEnum


class ReservationDelete(BaseModel):
    """Schema for reservation deletion."""

    is_deleted: bool = True
    deleted_at: datetime = Field(default_factory=datetime.utcnow)
