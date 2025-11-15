from app.core.db.crud import KodaiiCRUD
from ..models.tier import Tier
from ..schemas.tier import (
    TierCreateInternal,
    TierDelete,
    TierRead,
    TierUpdate,
    TierUpdateInternal,
)

CRUDTier = KodaiiCRUD[
    Tier, TierCreateInternal, TierUpdate, TierUpdateInternal, TierDelete, TierRead
]
crud_tiers = CRUDTier(Tier)
