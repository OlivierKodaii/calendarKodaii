from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, validator

from .enums import SlotStatusEnum


class SlotBase(BaseModel):
    """Base Slot model with core fields."""

    host_id: Annotated[
        UUID, Field(..., description="Reference to the host user who owns this slot")
    ]
    start_time: Annotated[
        datetime, Field(..., description="Slot start time in host's timezone")
    ]
    end_time: Annotated[
        datetime, Field(..., description="Slot end time in host's timezone")
    ]
    duration_minutes: Annotated[
        int, Field(..., ge=1, description="Duration of the slot in minutes")
    ]

    @validator("end_time")
    def validate_end_time_after_start_time(cls, v, values):
        if "start_time" in values and v <= values["start_time"]:
            raise ValueError("End time must be after start time")
        return v


class Slot(SlotBase):
    """Complete Slot model."""

    status: Annotated[
        SlotStatusEnum,
        Field(
            default=SlotStatusEnum.AVAILABLE, description="Current status of the slot"
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


class SlotRead(BaseModel):
    """Schema for reading slot data."""

    id: UUID
    host_id: UUID
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    status: SlotStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SlotCreate(SlotBase):
    """Schema for creating slots."""

    model_config = ConfigDict(extra="forbid")


class SlotCreateInternal(SlotBase):
    """Schema for internal slot creation."""

    status: Annotated[
        SlotStatusEnum,
        Field(
            default=SlotStatusEnum.AVAILABLE, description="Current status of the slot"
        ),
    ]


class SlotUpdate(BaseModel):
    """Schema for updating slots."""

    model_config = ConfigDict(extra="forbid")

    start_time: Annotated[
        Optional[datetime],
        Field(default=None, description="Slot start time in host's timezone"),
    ]
    end_time: Annotated[
        Optional[datetime],
        Field(default=None, description="Slot end time in host's timezone"),
    ]
    duration_minutes: Annotated[
        Optional[int],
        Field(default=None, ge=1, description="Duration of the slot in minutes"),
    ]
    status: Annotated[
        Optional[SlotStatusEnum],
        Field(default=None, description="Current status of the slot"),
    ]

    @validator("end_time")
    def validate_end_time_after_start_time(cls, v, values):
        if (
            v is not None
            and "start_time" in values
            and values["start_time"] is not None
            and v <= values["start_time"]
        ):
            raise ValueError("End time must be after start time")
        return v


class SlotUpdateInternal(SlotUpdate):
    """Schema for internal slot updates."""

    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SlotDelete(BaseModel):
    """Schema for slot deletion."""

    is_deleted: bool = True
    deleted_at: datetime = Field(default_factory=datetime.utcnow)
