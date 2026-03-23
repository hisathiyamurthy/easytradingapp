"""WebSocket service for real-time data."""
import json
import asyncio
from typing import Dict, Set, Optional
from datetime import datetime, timezone
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import decode_token


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "orders": set(),
            "positions": set(),
            "market_data": set(),
            "notifications": set(),
            "strategies": set(),
        }
        self.user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str, user_id: Optional[str] = None):
        """Connect a new WebSocket client."""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str, user_id: Optional[str] = None):
        """Disconnect a WebSocket client."""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)

        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    async def broadcast(self, message: dict, channel: str):
        """Broadcast message to all clients in a channel."""
        if channel in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)

            for conn in disconnected:
                self.active_connections[channel].discard(conn)

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast message to all connections for a specific user."""
        if user_id in self.user_connections:
            disconnected = set()
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)

            for conn in disconnected:
                self.user_connections[user_id].discard(conn)


manager = ConnectionManager()


class WebSocketHandler:
    """Handles WebSocket connections and messages."""

    def __init__(self, websocket: WebSocket, db: AsyncSession):
        self.websocket = websocket
        self.db = db
        self.user_id: Optional[str] = None
        self.channels: Set[str] = set()

    async def authenticate(self, token: str) -> bool:
        """Authenticate WebSocket connection using JWT token."""
        try:
            payload = decode_token(token)
            self.user_id = payload.get("sub")
            return True
        except Exception:
            return False

    async def handle_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "subscribe":
                channel = data.get("channel")
                if channel:
                    self.channels.add(channel)
                    await manager.connect(self.websocket, channel, self.user_id)

            elif msg_type == "unsubscribe":
                channel = data.get("channel")
                if channel in self.channels:
                    self.channels.discard(channel)
                    manager.disconnect(self.websocket, channel, self.user_id)

            elif msg_type == "ping":
                await self.websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

        except json.JSONDecodeError:
            await self.websocket.send_json({"type": "error", "message": "Invalid JSON"})

    async def handle_disconnect(self):
        """Handle WebSocket disconnect."""
        for channel in self.channels:
            manager.disconnect(self.websocket, channel, self.user_id)


async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """Main WebSocket endpoint."""
    db = None
    handler = None

    try:
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return

        from database.session import async_session
        db = async_session()
        
        handler = WebSocketHandler(websocket, db)
        
        if not await handler.authenticate(token):
            await websocket.close(code=4001, reason="Invalid token")
            return

        await manager.connect(websocket, "general", handler.user_id)

        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                await handler.handle_message(message)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        if handler:
            await handler.handle_disconnect()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if db:
            await db.close()


async def send_order_update(user_id: str, order_data: dict):
    """Send order update to user."""
    message = {
        "type": "order_update",
        "data": order_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast_to_user(user_id, message)


async def send_position_update(user_id: str, position_data: dict):
    """Send position update to user."""
    message = {
        "type": "position_update",
        "data": position_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast_to_user(user_id, message)


async def send_market_data_update(channel: str, market_data: dict):
    """Send market data update to channel."""
    message = {
        "type": "market_data",
        "data": market_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast(message, channel)


async def send_notification(user_id: str, notification_data: dict):
    """Send notification to user."""
    message = {
        "type": "notification",
        "data": notification_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast_to_user(user_id, message)


async def send_strategy_update(user_id: str, strategy_data: dict):
    """Send strategy update to user."""
    message = {
        "type": "strategy_update",
        "data": strategy_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast_to_user(user_id, message)
