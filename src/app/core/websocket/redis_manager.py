# src/app/core/websocket/redis_manager.py

import uuid
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisWebSocketManager:
    """Redis-backed WebSocket manager for coordination between API and worker processes"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.local_connections: Dict[str, WebSocket] = {}
        self.server_id = uuid.uuid4().hex[:8]
        self.pubsub = None
        self._initialized = False
        self._listener_task = None

    async def initialize(self):
        """Initialize Redis pub/sub listener"""
        if self._initialized:
            return

        if self.redis is None:
            raise RuntimeError("Redis client is not initialized")

        try:
            await self.redis.ping()
            self.pubsub = self.redis.pubsub()
            # Subscribe to ALL session channels with pattern
            await self.pubsub.psubscribe("session:*")

            self._listener_task = asyncio.create_task(self._redis_listener())
            self._initialized = True

            logger.info(
                f"✅ Redis WebSocket manager initialized for server {self.server_id}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis WebSocket manager: {e}")
            raise

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        session_id: int,
        user_id: int = None,
    ):
        """Connect WebSocket and register in Redis"""
        await websocket.accept()
        self.local_connections[connection_id] = websocket

        # Store connection info in Redis with expiration
        connection_info = {
            "server_id": self.server_id,
            "user_id": user_id,
            "connected_at": asyncio.get_event_loop().time(),
            "status": "active",
        }

        try:
            # Store in session-specific hash
            await self.redis.hset(
                f"session:{session_id}:connections",
                connection_id,
                json.dumps(connection_info),
            )
            await self.redis.expire(f"session:{session_id}:connections", 3600)

            # Store reverse mapping
            await self.redis.set(
                f"connection:{connection_id}:session", session_id, ex=3600
            )

            # Store connection count for debugging
            await self.redis.incr(f"session:{session_id}:connection_count")
            await self.redis.expire(f"session:{session_id}:connection_count", 3600)

            logger.info(
                f"WebSocket connected: {connection_id} for session {session_id} on server {self.server_id}"
            )

            # Verify registration worked
            count = await self.redis.hlen(f"session:{session_id}:connections")
            logger.info(f"Session {session_id} now has {count} registered connections")

        except Exception as e:
            logger.error(f"Failed to register connection in Redis: {e}")

    async def disconnect(self, connection_id: str):
        """Disconnect WebSocket and clean up Redis"""
        if connection_id in self.local_connections:
            del self.local_connections[connection_id]

        if not self._initialized:
            return

        try:
            session_id_bytes = await self.redis.get(
                f"connection:{connection_id}:session"
            )
            if session_id_bytes:
                session_id = int(session_id_bytes)
                await self.redis.hdel(
                    f"session:{session_id}:connections", connection_id
                )
                await self.redis.delete(f"connection:{connection_id}:session")
                await self.redis.decr(f"session:{session_id}:connection_count")

                count = await self.redis.hlen(f"session:{session_id}:connections")
                logger.info(
                    f"Session {session_id} now has {count} registered connections"
                )
        except Exception as e:
            logger.error(f"Failed to cleanup Redis connection: {e}")

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_to_session(self, session_id: int, message: dict) -> int:
        """Send message to all connections in a session via Redis pub/sub"""

        if not self._initialized:
            logger.warning("Redis not initialized, cannot send message")
            return 0

        try:
            # Add server_id to message to identify source
            message_with_server = {**message, "server_id": self.server_id}

            # Publish to Redis channel
            channel = f"session:{session_id}"
            published = await self.redis.publish(
                channel, json.dumps(message_with_server)
            )

            logger.info(
                f"📡 Published to Redis channel '{channel}' (subscribers: {published})"
            )

            # Also send to local connections immediately (don't wait for Redis round-trip)
            local_count = await self._send_to_local_connections(session_id, message)

            # Get total connection count from Redis
            total_count = await self.get_session_connection_count(session_id)

            logger.info(
                f"Message sent - Local: {local_count}, Total registered: {total_count}"
            )

            return total_count

        except Exception as e:
            logger.error(f"Failed to send message to session {session_id}: {e}")
            return 0

    async def get_session_connection_count(self, session_id: int) -> int:
        """Get total number of connections for a session"""
        try:
            count = await self.redis.hlen(f"session:{session_id}:connections")
            logger.info(
                f"Found {count} registered connections for session {session_id}"
            )
            return count
        except Exception as e:
            logger.error(f"Error getting connection count: {e}")
            return 0

    async def _send_to_local_connections(
        self, session_id: int, message: Dict[str, Any]
    ) -> int:
        """Send message to local connections for a session"""
        try:
            connections = await self.redis.hgetall(f"session:{session_id}:connections")
            sent_count = 0
            connections_to_remove = []

            for connection_id, connection_info_str in connections.items():
                connection_id = (
                    connection_id.decode()
                    if isinstance(connection_id, bytes)
                    else connection_id
                )

                try:
                    connection_info = json.loads(connection_info_str)

                    # Only send to connections on this server
                    if connection_info.get("server_id") == self.server_id:
                        if connection_id in self.local_connections:
                            websocket = self.local_connections[connection_id]
                            await websocket.send_json(message)
                            sent_count += 1
                            logger.debug(
                                f"✉️ Sent message to local connection {connection_id}"
                            )
                        else:
                            logger.warning(
                                f"Connection {connection_id} in Redis but not in local connections"
                            )
                            connections_to_remove.append(connection_id)
                except Exception as e:
                    logger.error(f"Error sending to connection {connection_id}: {e}")
                    connections_to_remove.append(connection_id)

            # Clean up stale connections
            for connection_id in connections_to_remove:
                await self.disconnect(connection_id)

            return sent_count
        except Exception as e:
            logger.error(f"Error in _send_to_local_connections: {e}")
            return 0

    async def _redis_listener(self):
        """Listen for Redis pub/sub messages"""
        try:
            if not self.pubsub:
                logger.error("Redis pub/sub not initialized")
                return

            logger.info(f"👂 Starting Redis listener for server {self.server_id}")

            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        channel = message["channel"].decode()
                        data = message["data"].decode()

                        # Extract session_id from channel name "session:8"
                        session_id = int(channel.split(":")[1])
                        message_data = json.loads(data)

                        logger.info(
                            f"📨 Received Redis message for session {session_id} from server {message_data.get('server_id', 'unknown')}"
                        )

                        # Forward to local connections (listener receives ALL messages including own)
                        await self._send_to_local_connections(session_id, message_data)

                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
        finally:
            logger.info("Redis listener ended")

    async def get_session_info(self, session_id: int) -> Dict[str, Any]:
        """Get debug info about session connections"""
        try:
            connections = await self.redis.hgetall(f"session:{session_id}:connections")
            connection_count = (
                await self.redis.get(f"session:{session_id}:connection_count") or 0
            )

            local_connections = list(self.local_connections.keys())

            return {
                "session_id": session_id,
                "total_connections": len(connections),
                "connection_count": int(connection_count),
                "local_connections": local_connections,
                "server_id": self.server_id,
                "redis_connections": [
                    k.decode() if isinstance(k, bytes) else k
                    for k in connections.keys()
                ],
            }
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {}

    async def cleanup(self):
        """Clean up resources"""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            try:
                await self.pubsub.close()
            except Exception as e:
                logger.error(f"Error closing pub/sub: {e}")

        self._initialized = False
        logger.info("WebSocket manager cleanup complete")
