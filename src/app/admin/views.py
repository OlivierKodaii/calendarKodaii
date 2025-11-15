from typing import Annotated


from app.core.db.crudadmin.admin_interface.model_view import PasswordTransformer
from pydantic import BaseModel, Field
from app.core.db.crudadmin.admin_interface.crud_admin import CRUDAdmin
from app.models.reservation import Reservation
from app.models.slot import Slot
from app.schemas.reservation import ReservationCreate, ReservationUpdate
from app.schemas.slot import SlotCreate, SlotUpdate

from ..core.security import get_password_hash
from ..models.tier import Tier
from ..models.user import User
from ..schemas.tier import TierCreate, TierUpdate
from ..schemas.user import UserCreate, UserUpdate


class PostCreateAdmin(BaseModel):
    title: Annotated[
        str, Field(min_length=2, max_length=30, examples=["This is my post"])
    ]
    text: Annotated[
        str,
        Field(
            min_length=1, max_length=63206, examples=["This is the content of my post."]
        ),
    ]
    created_by_user_id: int
    media_url: Annotated[
        str | None,
        Field(
            pattern=r"^(https?|ftp)://[^\s/$.?#].[^\s]*$",
            examples=["https://www.postimageurl.com"],
            default=None,
        ),
    ]


def register_admin_views(admin: CRUDAdmin) -> None:
    """Register all models and their schemas with the admin interface.

    This function adds all available models to the admin interface with appropriate
    schemas and permissions.
    """

    password_transformer = PasswordTransformer(
        password_field="password",
        hashed_field="hashed_password",
        hash_function=get_password_hash,
        required_fields=["name", "username", "email"],
    )

    admin.add_view(
        model=User,
        create_schema=UserCreate,
        update_schema=UserUpdate,
        allowed_actions={"view", "create", "update"},
        password_transformer=password_transformer,
    )

    admin.add_view(
        model=Tier,
        create_schema=TierCreate,
        update_schema=TierUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    admin.add_view(
        model=Slot,
        create_schema=SlotCreate,
        update_schema=SlotUpdate,
        allowed_actions={"view", "create", "update"},
    )

    admin.add_view(
        model=Reservation,
        create_schema=ReservationCreate,
        update_schema=ReservationUpdate,
        allowed_actions={"view", "create", "update"},
    )
