from datetime import datetime, UTC
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.db.database import async_get_db

from app.crud.crud_slot import crud_slots
from app.schemas.slot import (
    Slot,
    SlotCreate,
    SlotCreateInternal,
    SlotRead,
    SlotUpdate,
    SlotUpdateInternal,
    SlotDelete,
)
from app.api.dependencies import get_current_user
from app.core.db.paginated.helper import compute_offset
from app.core.db.paginated.response import paginated_response
from app.core.db.paginated.schemas import PaginatedListResponse

router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("/", response_model=PaginatedListResponse[SlotRead])
async def get_slots(
    host_id: Optional[UUID] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get all slots with optional filtering.

    This endpoint returns all slots, optionally filtered by host_id or status.
    Results are paginated.
    """
    # Calculate offset for pagination
    offset = compute_offset(page, items_per_page)

    # Prepare filter parameters
    filter_params = {}
    if host_id:
        filter_params["host_id"] = host_id
    if status:
        filter_params["status"] = status

    # Get results with pagination
    result = await crud_slots.get_multi(
        db=db,
        offset=offset,
        limit=items_per_page,
        schema_to_select=SlotRead,
        return_total_count=True,
        **filter_params,
    )

    # Create paginated response
    return paginated_response(data=result, page=page, items_per_page=items_per_page)


@router.get("/available", response_model=List[SlotRead])
async def get_available_slots(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    host_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get available slots with optional time range and host filters.
    """
    # Calculate offset for pagination
    offset = compute_offset(page, items_per_page)

    # Start with the status filter for available slots
    filter_params = {"status": "available"}

    # Add host_id filter if provided
    if host_id:
        filter_params["host_id"] = host_id

    # For time range filters, we need to use a more complex query
    # that we'll build using SQLAlchemy
    if start_time or end_time:
        # Create a base query for available slots
        query = select(Slot).where(Slot.status == "available")

        # Add host filter if provided
        if host_id:
            query = query.where(Slot.host_id == host_id)

        # Add time range filters
        if start_time:
            query = query.where(Slot.start_time >= start_time)
        if end_time:
            query = query.where(Slot.end_time <= end_time)

        # Apply pagination
        query = query.offset(offset).limit(items_per_page)

        # Execute query
        result = await db.execute(query)
        slots = result.scalars().all()

        return slots
    else:
        # If no time filters, use the simpler get_multi approach
        result = await crud_slots.get_multi(
            db=db,
            offset=offset,
            limit=items_per_page,
            schema_to_select=SlotRead,
            **filter_params,
        )

        return result["data"]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=SlotRead)
async def create_slot(
    slot_data: SlotCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Create a new slot.

    This endpoint allows a user to create a new slot.
    The current user will be set as the host.
    """
    # Validate end_time is after start_time
    if slot_data.end_time <= slot_data.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time",
        )

    # Calculate duration if not provided
    duration_minutes = slot_data.duration_minutes
    if not duration_minutes:
        duration = slot_data.end_time - slot_data.start_time
        duration_minutes = int(duration.total_seconds() / 60)

    # Create internal model with additional fields
    slot_internal = SlotCreateInternal(
        **slot_data.dict(),
        host_id=current_user.id,
        duration_minutes=duration_minutes,
        status="available",
        created_at=datetime.now(UTC),
    )

    # Create the slot
    new_slot = await crud_slots.create(
        db=db,
        object=slot_internal,
    )

    return new_slot


@router.get("/{slot_id}", response_model=SlotRead)
async def get_slot(
    slot_id: Annotated[UUID, Path(title="The ID of the slot to get")],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get a specific slot by ID.
    """
    slot = await crud_slots.get(db=db, id=slot_id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot with id {slot_id} not found",
        )

    return slot


@router.patch("/{slot_id}", response_model=SlotRead)
async def update_slot(
    slot_id: Annotated[UUID, Path(title="The ID of the slot to update")],
    slot_update: SlotUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Update a slot.

    This endpoint allows the host to update their slot.
    """
    # Check if slot exists
    slot = await crud_slots.get(db=db, id=slot_id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot with id {slot_id} not found",
        )

    # Check if user is authorized to update this slot
    if slot.host_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can update the slot",
        )

    # Validate time updates if both are provided
    start_time = slot_update.start_time if slot_update.start_time else slot.start_time
    end_time = slot_update.end_time if slot_update.end_time else slot.end_time

    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time",
        )

    # Update duration_minutes if times are changed
    update_dict = slot_update.dict(exclude_unset=True)
    if "start_time" in update_dict or "end_time" in update_dict:
        duration = end_time - start_time
        update_dict["duration_minutes"] = int(duration.total_seconds() / 60)

    # Add updated_at timestamp
    update_dict["updated_at"] = datetime.now(UTC)

    # Convert to internal update model
    slot_update_internal = SlotUpdateInternal(**update_dict)

    # Update the slot
    updated_slot = await crud_slots.update(
        db=db,
        id=slot_id,
        object=slot_update_internal,
    )

    return updated_slot


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: Annotated[UUID, Path(title="The ID of the slot to delete")],
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Delete a slot.

    This endpoint allows the host to delete their slot.
    """
    # Check if slot exists
    slot = await crud_slots.get(db=db, id=slot_id)
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot with id {slot_id} not found",
        )

    # Check if user is authorized to delete this slot
    if slot.host_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can delete the slot",
        )

    # Create delete model
    delete_data = SlotDelete(is_deleted=True, deleted_at=datetime.now(UTC))

    # Delete the slot (soft delete)
    await crud_slots.update(db=db, id=slot_id, object=delete_data)

    return None


@router.get("/host/{host_id}", response_model=List[SlotRead])
async def get_host_slots(
    host_id: Annotated[UUID, Path(title="The ID of the host")],
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get all slots for a specific host.
    """
    # Calculate offset for pagination
    offset = compute_offset(page, items_per_page)

    # Get slots for the host
    result = await crud_slots.get_multi(
        db=db,
        offset=offset,
        limit=items_per_page,
        schema_to_select=SlotRead,
        host_id=host_id,
    )

    return result["data"]
