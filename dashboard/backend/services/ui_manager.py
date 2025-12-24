"""UI client manager for Dashboard.

Manages WebSocket connections to UI clients and broadcasts cluster state updates.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class UIManager:
    """Manages WebSocket connections to UI clients.

    This service tracks all connected UI clients and broadcasts
    cluster state updates to them in real-time.
    """

    def __init__(self):
        """Initialize the UI manager."""
        self._clients: List[WebSocket] = []
        self._lock = asyncio.Lock()

        # Throttling: track last stats update time per machine
        self._last_stats_update: Dict[str, float] = {}
        self._stats_throttle_interval = 1.0  # Max 1 update per second per machine

        logger.info("ui_manager_initialized")

    async def add_client(self, websocket: WebSocket) -> None:
        """Add a UI client connection.

        Args:
            websocket: WebSocket connection to the UI client
        """
        async with self._lock:
            self._clients.append(websocket)

        logger.info(
            "ui_client_connected",
            total_clients=len(self._clients),
        )

    async def remove_client(self, websocket: WebSocket) -> None:
        """Remove a UI client connection.

        Args:
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            if websocket in self._clients:
                self._clients.remove(websocket)

        logger.info(
            "ui_client_disconnected",
            total_clients=len(self._clients),
        )

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected UI clients.

        Args:
            message: Message to broadcast
        """
        if not self._clients:
            return

        # Take snapshot of clients to avoid holding lock during sends
        async with self._lock:
            clients = self._clients.copy()

        # Send to all clients, removing any that fail
        failed_clients = []
        for client in clients:
            try:
                await client.send_json(message)
            except Exception as e:
                logger.warning(
                    "ui_broadcast_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                failed_clients.append(client)

        # Remove failed clients
        if failed_clients:
            async with self._lock:
                for client in failed_clients:
                    if client in self._clients:
                        self._clients.remove(client)

            logger.info(
                "ui_clients_removed",
                count=len(failed_clients),
                total_clients=len(self._clients),
            )

    async def broadcast_update(self, update_type: str, data: Dict[str, Any]) -> None:
        """Broadcast a cluster state update to all UI clients.

        Args:
            update_type: Type of update (e.g., "machine_connected", "stats_updated")
            data: Update data
        """
        # Apply throttling for stats updates
        if update_type == "stats_updated":
            machine_id = data.get("machine_id")
            if machine_id:
                now = asyncio.get_event_loop().time()
                last_update = self._last_stats_update.get(machine_id, 0)

                if now - last_update < self._stats_throttle_interval:
                    logger.debug(
                        "ui_update_throttled",
                        update_type=update_type,
                        machine_id=machine_id,
                    )
                    return

                # Update last update time
                self._last_stats_update[machine_id] = now

        message = {
            "type": update_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)

        logger.debug(
            "ui_update_broadcast",
            update_type=update_type,
            client_count=len(self._clients),
        )

    def get_client_count(self) -> int:
        """Get the number of connected UI clients.

        Returns:
            Number of connected clients
        """
        return len(self._clients)


# Singleton instance
ui_manager = UIManager()
