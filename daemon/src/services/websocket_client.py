"""WebSocket Client Service - Connects to Dashboard and handles bidirectional communication."""

import asyncio
import json
import random
from datetime import datetime
from typing import Any, Callable, Optional

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from src.config import config
from src.logger import logger
from src.protocol.jsonrpc import (
    build_notification,
    build_request,
    build_response,
    build_error_response,
    parse_message,
    JSONRPCRequest,
    JSONRPCNotification,
    ErrorCode,
)


class WebSocketClient:
    """
    WebSocket client for connecting to Dashboard control plane.

    Handles:
    - Connection to Dashboard with auto-reconnection
    - Daemon registration on connect
    - Stats reporting at regular intervals
    - Command handling from Dashboard (container.start, container.stop)
    - Exponential backoff with jitter for reconnection
    """

    def __init__(
        self,
        dashboard_url: str,
        stats_collector: Any,
        container_manager: Any,
    ):
        """
        Initialize WebSocket client.

        Args:
            dashboard_url: WebSocket URL of Dashboard (e.g., ws://dashboard:8080/ws/daemon)
            stats_collector: StatsCollector instance for gathering system metrics
            container_manager: ContainerManager instance for container operations
        """
        self.dashboard_url = dashboard_url
        self.stats_collector = stats_collector
        self.container_manager = container_manager
        self.machine_id = config.MACHINE_ID

        # Connection state
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected = False

        # Reconnection backoff parameters
        self.backoff = 1.0  # Initial backoff in seconds
        self.backoff_multiplier = 2.0
        self.max_backoff = 60.0
        self.jitter = 0.5  # +/- jitter in seconds

        # Request ID counter for JSON-RPC requests
        self._request_id = 0

        # Command handlers mapping
        self._command_handlers: dict[str, Callable] = {
            "container.start": self._handle_start,
            "container.stop": self._handle_stop,
        }

    async def connect(self) -> None:
        """
        Connect to Dashboard and maintain connection with automatic reconnection.

        This is the main entry point that runs indefinitely, reconnecting on failure.
        Uses exponential backoff with jitter for reconnection attempts.
        """
        while True:
            try:
                logger.info("Connecting to Dashboard", url=self.dashboard_url)

                async with websockets.connect(self.dashboard_url) as websocket:
                    self.websocket = websocket
                    self.connected = True

                    # Reset backoff on successful connection
                    self.backoff = 1.0

                    logger.info("Connected to Dashboard", url=self.dashboard_url)

                    # Send registration notification
                    await self._send_registration()

                    # Start message handling loop
                    await self._message_loop()

            except (ConnectionClosed, WebSocketException, OSError) as e:
                self.connected = False
                self.websocket = None

                logger.warning(
                    "Dashboard connection lost",
                    error=str(e),
                    backoff_seconds=self.backoff,
                )

                # Calculate backoff with jitter
                jittered_backoff = self.backoff + random.uniform(-self.jitter, self.jitter)
                jittered_backoff = max(0.1, jittered_backoff)  # Ensure positive

                await asyncio.sleep(jittered_backoff)

                # Increase backoff for next attempt
                self.backoff = min(self.backoff * self.backoff_multiplier, self.max_backoff)

            except Exception as e:
                self.connected = False
                self.websocket = None

                logger.error(
                    "Unexpected error in WebSocket connection",
                    error=str(e),
                    error_type=type(e).__name__,
                )

                # Use current backoff
                await asyncio.sleep(self.backoff)

    async def _send_registration(self) -> None:
        """
        Send daemon.register notification to Dashboard with machine info and initial stats.

        This is sent immediately after connection is established to register
        the daemon with the Dashboard.
        """
        try:
            # Collect current stats
            stats = await self.stats_collector.collect()

            # Build registration notification
            notification = build_notification(
                method="daemon.register",
                params={
                    "machine_id": self.machine_id,
                    "hostname": stats.hostname,
                    "stats": stats.to_dict(),
                },
            )

            # Send to Dashboard (convert dict to JSON)
            await self.websocket.send(json.dumps(notification))

            logger.info(
                "Sent registration to Dashboard",
                machine_id=self.machine_id,
                hostname=stats.hostname,
            )

        except Exception as e:
            logger.error(
                "Failed to send registration",
                error=str(e),
            )
            # Re-raise to trigger reconnection
            raise

    async def _message_loop(self) -> None:
        """
        Main message handling loop - receives and processes messages from Dashboard.

        Runs until connection is closed or an error occurs.
        """
        try:
            async for raw_message in self.websocket:
                try:
                    # Parse JSON-RPC message
                    message = parse_message(raw_message)

                    # Handle based on message type
                    if isinstance(message, JSONRPCRequest):
                        await self._handle_request(message)
                    elif isinstance(message, JSONRPCNotification):
                        await self._handle_notification(message)
                    else:
                        # Responses are not expected from Dashboard (we don't send requests)
                        logger.warning(
                            "Received unexpected message type",
                            message_type=type(message).__name__,
                        )

                except ValueError as e:
                    logger.error(
                        "Failed to parse message",
                        error=str(e),
                        raw_message=raw_message[:200],
                    )
                except Exception as e:
                    logger.error(
                        "Error handling message",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

        except ConnectionClosed:
            logger.info("WebSocket connection closed by Dashboard")
            raise
        except Exception as e:
            logger.error("Error in message loop", error=str(e))
            raise

    async def _handle_request(self, request: JSONRPCRequest) -> None:
        """
        Handle incoming JSON-RPC request from Dashboard.

        Dispatches to appropriate command handler and sends response back.

        Args:
            request: Parsed JSON-RPC request
        """
        method = request.method
        params = request.params or {}
        request_id = request.id

        logger.info(
            "Received command",
            method=method,
            params=params,
            request_id=request_id,
        )

        # Dispatch to handler
        handler = self._command_handlers.get(method)

        if handler is None:
            # Unknown method - send error response
            error_response = build_error_response(
                code=ErrorCode.METHOD_NOT_FOUND,
                message=f"Method not found: {method}",
                request_id=request_id,
            )
            await self.websocket.send(json.dumps(error_response))
            logger.warning("Unknown method", method=method)
            return

        try:
            # Call handler
            result = await handler(params)

            # Send success response
            response = build_response(result=result, request_id=request_id)
            await self.websocket.send(json.dumps(response))

            logger.info(
                "Command completed",
                method=method,
                request_id=request_id,
            )

        except Exception as e:
            # Handler raised exception - send error response
            error_response = build_error_response(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Internal error: {str(e)}",
                request_id=request_id,
            )
            await self.websocket.send(json.dumps(error_response))

            logger.error(
                "Command handler failed",
                method=method,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _handle_notification(self, notification: JSONRPCNotification) -> None:
        """
        Handle incoming JSON-RPC notification from Dashboard.

        Notifications don't require a response.

        Args:
            notification: Parsed JSON-RPC notification
        """
        method = notification.method
        params = notification.params or {}

        logger.debug(
            "Received notification",
            method=method,
            params=params,
        )

        # Currently no notifications are expected from Dashboard
        # But we log them for debugging
        logger.warning("Unexpected notification from Dashboard", method=method)

    async def _handle_start(self, params: dict) -> dict:
        """
        Handle container.start command (STUB).

        This is a stub implementation that logs params but doesn't actually start containers.
        Will be implemented fully in Phase 5.

        Args:
            params: Command parameters containing model_quant, runtime, gpus, config, etc.

        Returns:
            Response dict with container_id and status
        """
        model_quant = params.get("model_quant", "unknown")
        runtime = params.get("runtime", "vllm")
        gpus = params.get("gpus", [])

        logger.info(
            "STUB: Would start container",
            model_quant=model_quant,
            runtime=runtime,
            gpus=gpus,
            params=params,
        )

        # Generate stub container ID
        stub_container_id = f"stub-{model_quant}"

        # Schedule "ready" status notification after 2 seconds
        asyncio.create_task(self._send_ready_notification(model_quant, stub_container_id))

        return {
            "container_id": stub_container_id,
            "status": "starting",
        }

    async def _handle_stop(self, params: dict) -> dict:
        """
        Handle container.stop command (STUB).

        This is a stub implementation that logs params but doesn't actually stop containers.
        Will be implemented fully in Phase 5.

        Args:
            params: Command parameters containing model_quant and evicting flag

        Returns:
            Response dict with status
        """
        model_quant = params.get("model_quant", "unknown")
        evicting = params.get("evicting", False)

        logger.info(
            "STUB: Would stop container",
            model_quant=model_quant,
            evicting=evicting,
            params=params,
        )

        return {
            "status": "stopped",
        }

    async def _send_ready_notification(self, model_quant: str, container_id: str) -> None:
        """
        Send container.status notification after delay (for stub start command).

        Args:
            model_quant: Model quantization identifier
            container_id: Container ID
        """
        # Wait 2 seconds to simulate container startup
        await asyncio.sleep(2.0)

        if not self.connected or self.websocket is None:
            logger.debug("Skipping ready notification - not connected")
            return

        try:
            # Build status notification
            notification = build_notification(
                method="container.status",
                params={
                    "model_quant": model_quant,
                    "container_id": container_id,
                    "status": "ready",
                },
            )

            await self.websocket.send(json.dumps(notification))

            logger.info(
                "Sent container ready notification",
                model_quant=model_quant,
                container_id=container_id,
            )

        except Exception as e:
            logger.error(
                "Failed to send ready notification",
                error=str(e),
                model_quant=model_quant,
            )

    async def send_stats_report(self) -> None:
        """
        Collect and send stats.report notification to Dashboard.

        Called by stats reporting loop at regular intervals.
        """
        if not self.connected or self.websocket is None:
            logger.debug("Skipping stats report - not connected")
            return

        try:
            # Collect current stats
            stats = await self.stats_collector.collect()

            # Build stats notification
            notification = build_notification(
                method="stats.report",
                params={
                    "machine_id": self.machine_id,
                    "stats": stats.to_dict(),
                },
            )

            # Send to Dashboard (convert dict to JSON)
            await self.websocket.send(json.dumps(notification))

            logger.debug(
                "Sent stats report",
                machine_id=self.machine_id,
                timestamp=stats.timestamp.isoformat(),
            )

        except ConnectionClosed:
            logger.warning("Connection closed while sending stats")
            raise
        except Exception as e:
            logger.error(
                "Failed to send stats report",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't raise - allow stats loop to continue
