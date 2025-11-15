# For single server (development/small production)
# from .manager import WebSocketManager

# ws_manager = WebSocketManager()

# OR for multi-server production with Redis
# from .redis_manager import RedisWebSocketManager
# from app.core.utils.cache import client

# import logging
#
# logger = logging.getLogger(__name__)
#
# try:
#    # Get the Redis client and create WebSocket manager
#    redis_client = ensure_redis_client()
#    ws_manager = RedisWebSocketManager(redis_client)
#    logger.info("Redis WebSocket manager created successfully")
# except Exception as e:
#    logger.error(f"Failed to create Redis WebSocket manager: {e}")
#    # Fallback to a basic manager if needed
#    from .manager import WebSocketManager
#
#    ws_manager = WebSocketManager()
#    logger.info("Fallback to basic WebSocket manager")
#
# __all__ = ["ws_manager"]

# ws_manager = RedisWebSocketManager(client)

# __all__ = ["ws_manager"]

import logging
from typing import Optional
from .redis_manager import RedisWebSocketManager

logger = logging.getLogger(__name__)

# This will be initialized during application startup
ws_manager: Optional[RedisWebSocketManager] = None


async def initialize_websocket_manager():
    """Initialize WebSocket manager with Redis client"""
    global ws_manager

    try:
        # Import here to avoid circular imports
        from app.core.utils.cache import client

        redis_client = client

        if redis_client is None:
            logger.warning(
                "Redis client not available, WebSocket functionality will be limited"
            )
            # You could fallback to a basic manager here if needed
            # from .manager import WebSocketManager
            # ws_manager = WebSocketManager()
            return None

        ws_manager = RedisWebSocketManager(redis_client)
        await ws_manager.initialize()

        logger.info(f"WebSocket manager initialized with Redis support")
        return ws_manager

    except Exception as e:
        logger.error(f"Failed to initialize WebSocket manager: {e}")
        return None


async def cleanup_websocket_manager():
    """Cleanup WebSocket manager"""
    global ws_manager

    if ws_manager and hasattr(ws_manager, "cleanup"):
        try:
            await ws_manager.cleanup()
            logger.info("WebSocket manager cleanup completed")
        except Exception as e:
            logger.error(f"Error during WebSocket cleanup: {e}")

    ws_manager = None


def get_websocket_manager() -> Optional[RedisWebSocketManager]:
    """Get the WebSocket manager instance"""
    return ws_manager


__all__ = [
    "ws_manager",
    "initialize_websocket_manager",
    "cleanup_websocket_manager",
    "get_websocket_manager",
]
