from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio
from datetime import datetime

router = APIRouter()


# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.alert_subscribers: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, connection_type: str = "general"):
        await websocket.accept()
        self.active_connections.append(websocket)
        if connection_type == "alerts":
            self.alert_subscribers.append(websocket)
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.alert_subscribers:
            self.alert_subscribers.remove(websocket)
        print(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def broadcast_alert(self, alert_data: Dict):
        """Broadcast new alert to all alert subscribers"""
        message = json.dumps(
            {
                "type": "new_alert",
                "data": alert_data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        disconnected = []
        for connection in self.alert_subscribers:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_alert_update(self, alert_data: Dict):
        """Broadcast alert update to all alert subscribers"""
        message = json.dumps(
            {
                "type": "alert_updated",
                "data": alert_data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        disconnected = []
        for connection in self.alert_subscribers:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_stats(self, stats_data: Dict):
        """Broadcast updated statistics to all connections"""
        message = json.dumps(
            {
                "type": "stats_updated",
                "data": stats_data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time alert notifications"""
    await manager.connect(websocket, "alerts")

    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            json.dumps(
                {
                    "type": "connected",
                    "message": "Connected to alert notifications",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            websocket,
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (ping/pong for keepalive)
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    await manager.send_personal_message(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                        ),
                        websocket,
                    )

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/general")
async def websocket_general_endpoint(websocket: WebSocket):
    """WebSocket endpoint for general notifications (stats, etc.)"""
    await manager.connect(websocket, "general")

    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            json.dumps(
                {
                    "type": "connected",
                    "message": "Connected to general notifications",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            websocket,
        )

        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    await manager.send_personal_message(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                        ),
                        websocket,
                    )

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# Function to broadcast alerts (called from Celery tasks)
async def broadcast_new_alert(alert_data: Dict):
    """Function to broadcast new alert to all connected clients"""
    await manager.broadcast_alert(alert_data)


async def broadcast_alert_update(alert_data: Dict):
    """Function to broadcast alert update to all connected clients"""
    await manager.broadcast_alert_update(alert_data)


async def broadcast_stats_update(stats_data: Dict):
    """Function to broadcast stats update to all connected clients"""
    await manager.broadcast_stats(stats_data)
