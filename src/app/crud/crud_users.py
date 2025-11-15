from app.core.db.crud import KodaiiCRUD

from ..models.user import User
from ..schemas.user import (
    UserCreateInternal,
    UserDelete,
    UserRead,
    UserUpdate,
    UserUpdateInternal,
)

CRUDUser = KodaiiCRUD[
    User, UserCreateInternal, UserUpdate, UserUpdateInternal, UserDelete, UserRead
]
crud_users = CRUDUser(User)
