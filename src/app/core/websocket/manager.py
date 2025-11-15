# src/app/core/websocket/manager.py

import uuid
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Production WebSocket manager for session-based real-time updates"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[int, List[str]] = (
            {}
        )  # session_id -> [connection_ids]
        self.user_connections: Dict[int, List[str]] = {}  # user_id -> [connection_ids]

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        session_id: int,
        user_id: int = None,
    ):
        """Connect a WebSocket and associate it with a session and user"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket

        # Associate with session
        if session_id not in self.session_connections:
            self.session_connections[session_id] = []
        self.session_connections[session_id].append(connection_id)

        # Associate with user (optional)
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(connection_id)

        logger.info(f"WebSocket connected: {connection_id} for session {session_id}")

    def disconnect(self, connection_id: str, session_id: int, user_id: int = None):
        """Disconnect a WebSocket"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # Remove from session connections
        if session_id in self.session_connections:
            if connection_id in self.session_connections[session_id]:
                self.session_connections[session_id].remove(connection_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]

        # Remove from user connections
        if user_id and user_id in self.user_connections:
            if connection_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_to_session(self, session_id: int, message: Dict[str, Any]) -> int:
        """Send message to all connections for a specific session"""
        if session_id not in self.session_connections:
            logger.warning(f"No active connections for session {session_id}")
            return 0

        connections_to_remove = []
        sent_count = 0

        for connection_id in self.session_connections[session_id]:
            if connection_id in self.active_connections:
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_json(message)
                    sent_count += 1
                    logger.debug(f"Sent message to {connection_id}: {message['type']}")
                except Exception as e:
                    logger.error(f"Error sending to {connection_id}: {e}")
                    connections_to_remove.append(connection_id)

        # Clean up failed connections
        for connection_id in connections_to_remove:
            self.disconnect(connection_id, session_id)

        return sent_count

    async def send_to_user(self, user_id: int, message: Dict[str, Any]) -> int:
        """Send message to all connections for a specific user"""
        if user_id not in self.user_connections:
            logger.warning(f"No active connections for user {user_id}")
            return 0

        connections_to_remove = []
        sent_count = 0

        for connection_id in self.user_connections[user_id]:
            if connection_id in self.active_connections:
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending to {connection_id}: {e}")
                    connections_to_remove.append(connection_id)

        # Clean up failed connections
        for connection_id in connections_to_remove:
            # Note: We need session_id to clean up properly
            # This is a limitation of the current design
            pass

        return sent_count

    def get_session_connection_count(self, session_id: int) -> int:
        """Get number of active connections for a session"""
        return len(self.session_connections.get(session_id, []))

    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
