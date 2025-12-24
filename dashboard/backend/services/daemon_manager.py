"""Daemon connection manager for Dashboard.

Tracks active daemon WebSocket connections and handles command sending
and response matching.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class DaemonManager:
    """Manages WebSocket connections to daemons and command routing.

    This service tracks all active daemon connections, sends commands to specific
    daemons, and matches responses to pending requests.
    """

    def __init__(self):
        """Initialize the daemon manager."""
        # Active WebSocket connections by machine_id
        self._connections: Dict[str, WebSocket] = {}

        # Connection metadata
        self._connection_times: Dict[str, datetime] = {}
        self._last_seen: Dict[str, datetime] = {}

        # Request tracking for request/response matching
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._request_id_counter = 0
        self._lock = asyncio.Lock()

        logger.info("daemon_manager_initialized")

    async def register(self, machine_id: str, websocket: WebSocket) -> None:
        """Register a daemon connection.

        Args:
            machine_id: Unique identifier for the machine
            websocket: WebSocket connection to the daemon
        """
        async with self._lock:
            now = datetime.now()
            self._connections[machine_id] = websocket
            self._connection_times[machine_id] = now
            self._last_seen[machine_id] = now

        logger.info(
            "daemon_registered",
            machine_id=machine_id,
            total_connections=len(self._connections),
        )

    async def unregister(self, machine_id: str) -> None:
        """Unregister a daemon connection.

        Args:
            machine_id: Unique identifier for the machine
        """
        async with self._lock:
            if machine_id in self._connections:
                del self._connections[machine_id]
                del self._connection_times[machine_id]
                # Keep last_seen for historical purposes

        logger.info(
            "daemon_unregistered",
            machine_id=machine_id,
            total_connections=len(self._connections),
        )

    async def update_last_seen(self, machine_id: str) -> None:
        """Update the last_seen timestamp for a daemon.

        Args:
            machine_id: Unique identifier for the machine
        """
        async with self._lock:
            self._last_seen[machine_id] = datetime.now()

    def get_websocket(self, machine_id: str) -> Optional[WebSocket]:
        """Get the WebSocket connection for a machine.

        Args:
            machine_id: Unique identifier for the machine

        Returns:
            WebSocket connection or None if not connected
        """
        return self._connections.get(machine_id)

    async def get_daemon(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Get daemon connection information by machine_id.

        Args:
            machine_id: Unique identifier for the machine

        Returns:
            Dict with connection info or None if not connected
        """
        async with self._lock:
            if machine_id not in self._connections:
                return None

            return {
                "machine_id": machine_id,
                "connected_at": self._connection_times.get(machine_id),
                "last_seen": self._last_seen.get(machine_id),
            }

    async def get_all_daemons(self) -> Dict[str, Dict[str, Any]]:
        """Get all active daemon connections with metadata.

        Returns:
            Dict mapping machine_id to connection info
        """
        async with self._lock:
            result = {}
            for machine_id in self._connections.keys():
                result[machine_id] = {
                    "machine_id": machine_id,
                    "connected_at": self._connection_times.get(machine_id),
                    "last_seen": self._last_seen.get(machine_id),
                }
            return result

    def is_connected(self, machine_id: str) -> bool:
        """Check if a daemon is connected.

        Args:
            machine_id: Unique identifier for the machine

        Returns:
            True if connected, False otherwise
        """
        return machine_id in self._connections

    def list_connected(self) -> list[str]:
        """List all connected daemon machine IDs.

        Returns:
            List of machine IDs
        """
        return list(self._connections.keys())

    async def send_notification(
        self,
        machine_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a JSON-RPC notification to a daemon (no response expected).

        Args:
            machine_id: Target machine ID
            method: JSON-RPC method name
            params: Optional parameters

        Returns:
            True if sent successfully, False if daemon not connected
        """
        websocket = self.get_websocket(machine_id)
        if not websocket:
            logger.warning(
                "send_notification_failed_not_connected",
                machine_id=machine_id,
                method=method,
            )
            return False

        message = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            message["params"] = params

        try:
            await websocket.send_json(message)
            logger.debug(
                "notification_sent",
                machine_id=machine_id,
                method=method,
            )
            return True
        except Exception as e:
            logger.error(
                "send_notification_failed",
                machine_id=machine_id,
                method=method,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def send_request(
        self,
        machine_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Any:
        """Send a JSON-RPC request to a daemon and wait for response.

        Args:
            machine_id: Target machine ID
            method: JSON-RPC method name
            params: Optional parameters
            timeout: Request timeout in seconds

        Returns:
            Response result from daemon

        Raises:
            ValueError: If daemon not connected
            asyncio.TimeoutError: If request times out
            Exception: If daemon returns error response
        """
        websocket = self.get_websocket(machine_id)
        if not websocket:
            raise ValueError(f"Daemon {machine_id} not connected")

        # Generate request ID
        async with self._lock:
            self._request_id_counter += 1
            request_id = self._request_id_counter

        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request_id] = future

        # Build request message
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            message["params"] = params

        try:
            # Send request
            await websocket.send_json(message)
            logger.debug(
                "request_sent",
                machine_id=machine_id,
                method=method,
                request_id=request_id,
            )

            # Wait for response with timeout
            result = await asyncio.wait_for(future, timeout=timeout)
            return result

        except asyncio.TimeoutError:
            logger.error(
                "request_timeout",
                machine_id=machine_id,
                method=method,
                request_id=request_id,
                timeout=timeout,
            )
            raise
        except Exception as e:
            logger.error(
                "send_request_failed",
                machine_id=machine_id,
                method=method,
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            # Clean up pending request
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]

    async def handle_response(self, response: Dict[str, Any]) -> None:
        """Handle a JSON-RPC response from a daemon.

        Matches the response to a pending request and resolves the future.

        Args:
            response: JSON-RPC response message
        """
        request_id = response.get("id")
        if request_id is None:
            logger.warning("response_missing_id", response=response)
            return

        future = self._pending_requests.get(request_id)
        if future is None:
            logger.warning(
                "response_no_pending_request",
                request_id=request_id,
            )
            return

        # Check for error response
        if "error" in response:
            error = response["error"]
            error_msg = error.get("message", "Unknown error")
            error_code = error.get("code", -1)

            logger.error(
                "response_error",
                request_id=request_id,
                error_code=error_code,
                error_message=error_msg,
            )

            future.set_exception(
                Exception(f"JSON-RPC error {error_code}: {error_msg}")
            )
        else:
            # Success response
            result = response.get("result")
            future.set_result(result)

            logger.debug(
                "response_handled",
                request_id=request_id,
            )


# Singleton instance
daemon_manager = DaemonManager()
