# src/app/main.py

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from .admin.initialize import create_admin_interface
from .api import router
from .core.config import settings
from .core.setup import create_application, lifespan_factory

logger = logging.getLogger(__name__)

admin = create_admin_interface()


@asynccontextmanager
async def lifespan_with_admin(app: FastAPI) -> AsyncGenerator[None, None]:
    """Custom lifespan that includes Redis cache, WebSocket, and admin initialization."""
    # Startup
    logger.info("Starting up FastAPI application...")

    # Get the default lifespan
    default_lifespan = lifespan_factory(settings)

    # Run the default lifespan initialization
    async with default_lifespan(app):
        # Initialize Redis cache first
        try:
            from .core.utils.cache import client  # initialize_cache

            redis_client = client  # await initialize_cache()
            logger.info(
                f"Redis cache initialization: {'successful' if redis_client else 'failed'}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")

        # Initialize WebSocket manager (depends on Redis)
        try:
            from .core.websocket import initialize_websocket_manager

            ws_manager = await initialize_websocket_manager()
            logger.info(
                f"WebSocket manager initialization: {'successful' if ws_manager else 'failed'}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket manager: {e}")

        # Initialize admin interface if it exists
        if admin:
            try:
                await admin.initialize()
                logger.info("Admin interface initialized")
            except Exception as e:
                logger.error(f"Failed to initialize admin interface: {e}")

        yield  # Application runs here

    # Shutdown
    logger.info("Shutting down FastAPI application...")

    # Cleanup WebSocket manager
    try:
        from .core.websocket import cleanup_websocket_manager

        await cleanup_websocket_manager()
    except Exception as e:
        logger.error(f"Error during WebSocket cleanup: {e}")

    # Cleanup Redis cache
    try:
        from .core.utils.cache import close_cache

        await close_cache()
    except Exception as e:
        logger.error(f"Error during Redis cache cleanup: {e}")


app = create_application(
    router=router,
    settings=settings,
    create_tables_on_start=True,
    lifespan=lifespan_with_admin,
)

# Mount admin interface if enabled
if admin:
    app.mount(settings.CRUD_ADMIN_MOUNT_PATH, admin.app)
