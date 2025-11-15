from app.core.db.crud import KodaiiCRUD

from ..models.reservation import Reservation
from ..schemas.reservation import (
    ReservationCreateInternal,
    ReservationDelete,
    ReservationRead,
    ReservationUpdate,
    ReservationUpdateInternal,
)

CRUDReservation = KodaiiCRUD[
    Reservation,
    ReservationCreateInternal,
    ReservationUpdate,
    ReservationUpdateInternal,
    ReservationDelete,
    ReservationRead,
]
crud_reservations = CRUDReservation(Reservation)
