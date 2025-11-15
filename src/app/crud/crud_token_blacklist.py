from app.core.db.crud import KodaiiCRUD
from ..models.token_blacklist import TokenBlacklist
from ..core.schemas import (
    TokenBlacklistCreate,
    TokenBlacklistRead,
    TokenBlacklistUpdate,
)

CRUDTokenBlacklist = KodaiiCRUD[
    TokenBlacklist,
    TokenBlacklistCreate,
    TokenBlacklistUpdate,
    TokenBlacklistUpdate,
    TokenBlacklistUpdate,
    TokenBlacklistRead,
]
crud_token_blacklist = CRUDTokenBlacklist(TokenBlacklist)
