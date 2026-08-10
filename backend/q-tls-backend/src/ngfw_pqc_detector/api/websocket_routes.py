"""
WebSocket Routes for Real-time Analytics
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from ngfw_pqc_detector.services.analytics_engine import SuricataAnalytics
from ngfw_pqc_detector.core.config import settings

logger = logging.getLogger(__name__)

# Create WebSocket router
ws_router = APIRouter()

# Initialize analytics engine
analytics = SuricataAnalytics()


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(
            f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}"
        )

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        # Convert datetime objects to JSON-serializable format
        json_message = jsonable_encoder(message)
        
        for connection in self.active_connections:
            try:
                await connection.send_json(json_message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        self.active_connections -= disconnected


# Create connection managers for all WebSocket endpoints
batch_manager = ConnectionManager()
data_manager = ConnectionManager()
kafka_stream_manager = ConnectionManager()
alerts_manager = ConnectionManager()


@ws_router.websocket("/ws/batch-updates")
async def websocket_batch_updates(websocket: WebSocket):
    """
    WebSocket endpoint for batch processing updates
    Sends complete dashboard data every BATCH_INTERVAL seconds
    """
    await batch_manager.connect(websocket)

    try:
        # Send initial data immediately
        initial_data = await analytics.get_dashboard_summary(settings.ANALYTICS_TIME_WINDOW)
        initial_data["server_timestamp"] = datetime.utcnow().isoformat()
        initial_data["batch_interval"] = settings.ANALYTICS_BATCH_INTERVAL

        await websocket.send_json({"type": "initial_data", "data": initial_data})

        # Keep connection alive and wait for client messages (if any)
        while True:
            try:
                # Wait for client messages (ping/pong, etc.)
                data = await websocket.receive_text()

                # Handle client requests
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Batch WebSocket error: {e}", exc_info=True)
    finally:
        batch_manager.disconnect(websocket)


@ws_router.websocket("/ws/data-updates")
async def websocket_data_updates(websocket: WebSocket):
    """
    WebSocket endpoint for on-demand data updates
    Clients can request specific data by sending commands
    """
    await data_manager.connect(websocket)

    try:
        while True:
            # Receive command from client
            message = await websocket.receive_text()

            try:
                command = json.loads(message)
                action = command.get("action")
                params = command.get("params", {})

                response = {"type": "response", "action": action}

                # Handle different actions
                if action == "get_dashboard":
                    time_window = params.get("time_window", settings.ANALYTICS_TIME_WINDOW)
                    response["data"] = await analytics.get_dashboard_summary(time_window)

                elif action == "get_metrics":
                    time_window = params.get("time_window", settings.ANALYTICS_TIME_WINDOW)
                    response["data"] = {
                        "total_flows": await analytics.get_total_flows(time_window),
                        "tls_connections": await analytics.get_tls_connections(time_window),
                        "pqc_safe": await analytics.get_pqc_safe_connections(time_window),
                        "vulnerable": await analytics.get_vulnerable_connections(time_window),
                    }

                elif action == "get_live_flows":
                    limit = params.get("limit", 50)
                    response["data"] = await analytics.get_live_network_flows(limit)

                elif action == "get_alerts":
                    limit = params.get("limit", 10)
                    response["data"] = await analytics.get_security_alerts(limit)

                elif action == "get_protocol_distribution":
                    time_window = params.get("time_window", settings.ANALYTICS_TIME_WINDOW)
                    limit = params.get("limit", 10)
                    response["data"] = await analytics.get_protocol_distribution(time_window, limit)

                elif action == "get_pqc_distribution":
                    time_window = params.get("time_window", settings.ANALYTICS_TIME_WINDOW)
                    response["data"] = await analytics.get_pqc_status_distribution(time_window)

                elif action == "ping":
                    response["data"] = {"status": "pong"}

                else:
                    response["error"] = f"Unknown action: {action}"

                response["timestamp"] = datetime.utcnow().isoformat()
                await websocket.send_json(response)

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
            except Exception as e:
                logger.error(f"Error processing WebSocket command: {e}", exc_info=True)
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Data WebSocket error: {e}", exc_info=True)
    finally:
        data_manager.disconnect(websocket)


@ws_router.websocket("/ws/kafka-stream")
async def websocket_kafka_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time Kafka log streaming
    Streams TLS connection logs as they are consumed from Kafka
    """
    await kafka_stream_manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Connected to Kafka stream",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep connection alive and wait for client messages
        while True:
            try:
                # Wait for client messages (ping/pong, etc.)
                data = await websocket.receive_text()

                # Handle client requests
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Kafka stream WebSocket error: {e}", exc_info=True)
    finally:
        kafka_stream_manager.disconnect(websocket)


@ws_router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time security alerts
    Streams security alerts as they are created
    """
    await alerts_manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Connected to alerts stream",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Keep connection alive and wait for client messages
        while True:
            try:
                # Wait for client messages (ping/pong, etc.)
                data = await websocket.receive_text()

                # Handle client requests
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"Alerts WebSocket error: {e}", exc_info=True)
    finally:
        alerts_manager.disconnect(websocket)


async def broadcast_alert(alert: dict):
    """
    Broadcast alert to all connected alert clients
    This should be called from the alert service when a new alert is created
    """
    if alerts_manager.active_connections:
        await alerts_manager.broadcast(
            {"type": "alert", "data": alert, "timestamp": datetime.utcnow().isoformat()}
        )
        logger.info(f"🚨 Broadcasted alert to {len(alerts_manager.active_connections)} clients")


async def broadcast_kafka_message(message: dict):
    """
    Broadcast Kafka message to all connected kafka-stream clients
    This should be called from the Kafka consumer when a new message arrives
    """
    if kafka_stream_manager.active_connections:
        await kafka_stream_manager.broadcast(
            {"type": "kafka_message", "data": message, "timestamp": datetime.utcnow().isoformat()}
        )
        logger.debug(
            f"Broadcasted Kafka message to {len(kafka_stream_manager.active_connections)} clients"
        )


async def batch_processing_task():
    """
    Background task that sends analytics updates every BATCH_INTERVAL seconds
    """
    logger.info(f"Starting batch processing task (interval: {settings.ANALYTICS_BATCH_INTERVAL}s)")

    while True:
        try:
            # Get dashboard data
            dashboard_data = await analytics.get_dashboard_summary(settings.ANALYTICS_TIME_WINDOW)

            # Add timestamp
            dashboard_data["server_timestamp"] = datetime.utcnow().isoformat()
            dashboard_data["batch_interval"] = settings.ANALYTICS_BATCH_INTERVAL

            # Broadcast to all connected batch clients
            if batch_manager.active_connections:
                await batch_manager.broadcast({"type": "batch_update", "data": dashboard_data})
                logger.debug(
                    f"Broadcasted batch update to {len(batch_manager.active_connections)} clients"
                )

            # Wait for next interval
            await asyncio.sleep(settings.ANALYTICS_BATCH_INTERVAL)

        except Exception as e:
            logger.error(f"Error in batch processing: {e}", exc_info=True)
            await asyncio.sleep(5)  # Wait before retry
