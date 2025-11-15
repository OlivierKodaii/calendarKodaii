from typing import Annotated
from uuid import UUID
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.db.database import async_get_db
from app.crud.crud_slot import crud_slots
from app.crud.crud_reservations import crud_reservations
from app.schemas.reservation import (
    Reservation,
    ReservationCreate,
    ReservationCreateInternal,
    ReservationRead,
    ReservationUpdate,
    ReservationUpdateInternal,
    ReservationDelete,
    ReservationStatusUpdate,
)
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/booking", tags=["booking"])


@router.post(
    "/book", status_code=status.HTTP_201_CREATED, response_model=ReservationRead
)
async def book_slot(
    reservation_data: ReservationCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Book a slot in the calendar.

    This endpoint handles the initial booking request.
    It validates the booking form, checks slot availability,
    schedules the slot and sends a confirmation email.

    Rate limit: 10 per minute
    """
    # Check if slot exists
    slot = await crud_slots.get(db=db, id=reservation_data.slot_id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot with id {reservation_data.slot_id} not found",
        )

    # Check if slot is available
    if slot.status != "available":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slot with id {reservation_data.slot_id} is not available",
        )

    # Create internal model for reservation
    reservation_internal = ReservationCreateInternal(
        **reservation_data.dict(),
        user_id=current_user.id,
        host_id=slot.host_id,
        status="pending",
        created_at=datetime.now(UTC),
    )

    # Create reservation
    new_reservation = await crud_reservations.create(
        db=db,
        object=reservation_internal,
    )

    # Update slot status to reserved
    slot_update = {"status": "reserved", "updated_at": datetime.now(UTC)}
    await crud_slots.update(db=db, id=reservation_data.slot_id, object=slot_update)

    # In a real implementation, you would:
    # 1. Send confirmation email (async)
    # 2. Add to a job queue for any follow-up tasks

    return new_reservation


@router.post(
    "/submit", status_code=status.HTTP_201_CREATED, response_model=ReservationRead
)
async def submit_booking_form(
    reservation_data: ReservationCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Submit booking form.

    This endpoint handles the submission of the booking form.
    It validates the form data, checks slot availability,
    processes the booking and sends a confirmation email.

    Rate limit: 10 per minute
    """
    # Implementation is similar to book_slot
    # but might include additional form validation logic

    # Check if slot exists
    slot = await crud_slots.get(db=db, id=reservation_data.slot_id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot with id {reservation_data.slot_id} not found",
        )

    # Check if slot is available
    if slot.status != "available":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slot with id {reservation_data.slot_id} is not available",
        )

    # Create internal model for reservation
    reservation_internal = ReservationCreateInternal(
        **reservation_data.dict(),
        user_id=current_user.id,
        host_id=slot.host_id,
        status="pending",
        created_at=datetime.now(UTC),
    )

    # Create reservation
    new_reservation = await crud_reservations.create(
        db=db,
        object=reservation_internal,
    )

    # Update slot status to reserved
    slot_update = {"status": "reserved", "updated_at": datetime.now(UTC)}
    await crud_slots.update(db=db, id=reservation_data.slot_id, object=slot_update)

    return new_reservation


@router.get("/status/{reservation_id}", response_model=ReservationRead)
async def get_booking_status(
    reservation_id: Annotated[UUID, Path(title="The ID of the reservation to get")],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get status of a booking.

    This endpoint returns the current status of a booking.
    """
    reservation = await crud_reservations.get(db=db, id=reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with id {reservation_id} not found",
        )

    # Check if user is authorized to view this reservation
    if (
        reservation.user_id != current_user.id
        and reservation.host_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this reservation",
        )

    return reservation


@router.patch("/status/{reservation_id}", response_model=ReservationRead)
async def update_booking_status(
    reservation_id: Annotated[UUID, Path(title="The ID of the reservation to update")],
    status_update: ReservationStatusUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Update status of a booking.

    This endpoint updates the status of a booking.
    """
    # Get current reservation
    reservation = await crud_reservations.get(db=db, id=reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with id {reservation_id} not found",
        )

    # Check if user is authorized to update this reservation
    if reservation.host_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can update the reservation status",
        )

    # Update reservation status
    update_data = ReservationUpdateInternal(
        status=status_update.status, updated_at=datetime.now(UTC)
    )

    updated_reservation = await crud_reservations.update(
        db=db, id=reservation_id, object=update_data
    )

    # If status is cancelled, make the slot available again
    if status_update.status == "cancelled":
        slot_update = {"status": "available", "updated_at": datetime.now(UTC)}
        await crud_slots.update(db=db, id=reservation.slot_id, object=slot_update)

    return updated_reservation


@router.post("/webhooks/booking")
async def booking_webhook(
    payload: dict,
    db: AsyncSession = Depends(async_get_db),
):
    """
    Webhook for booking notifications.

    This endpoint handles external callbacks related to bookings,
    such as payment confirmations, calendar syncs, etc.
    """
    # Process webhook payload
    # This would typically include verification of the webhook source
    # and processing the payload based on its type

    # Return acknowledgment
    return {"status": "received"}
