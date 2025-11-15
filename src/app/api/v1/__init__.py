from fastapi import APIRouter

from .login import router as login_router
from .logout import router as logout_router
from .rate_limits import router as rate_limits_router
from .tasks import router as tasks_router
from .users import router as users_router
from .slots import router as slots_router
from .booking import router as booking_router

router = APIRouter(prefix="/v1")
router.include_router(login_router)
router.include_router(logout_router)
router.include_router(users_router)
router.include_router(tasks_router)
router.include_router(rate_limits_router)
router.include_router(booking_router)
router.include_router(slots_router)
