from app.core.db.crud import KodaiiCRUD

from ..models.slot import Slot
from ..schemas.slot import (
    SlotCreateInternal,
    SlotDelete,
    SlotRead,
    SlotUpdate,
    SlotUpdateInternal,
)

CRUDSlot = KodaiiCRUD[
    Slot, SlotCreateInternal, SlotUpdate, SlotUpdateInternal, SlotDelete, SlotRead
]
crud_slots = CRUDSlot(Slot)
