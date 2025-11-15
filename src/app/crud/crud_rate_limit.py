from app.core.db.crud import KodaiiCRUD

from ..models.rate_limit import RateLimit
from ..schemas.rate_limit import (
    RateLimitCreateInternal,
    RateLimitDelete,
    RateLimitRead,
    RateLimitUpdate,
    RateLimitUpdateInternal,
)

CRUDRateLimit = KodaiiCRUD[
    RateLimit,
    RateLimitCreateInternal,
    RateLimitUpdate,
    RateLimitUpdateInternal,
    RateLimitDelete,
    RateLimitRead,
]
crud_rate_limits = CRUDRateLimit(RateLimit)
