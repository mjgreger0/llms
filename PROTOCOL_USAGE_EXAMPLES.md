# JSON-RPC 2.0 Protocol - Usage Examples

This document provides practical examples of how to use the JSON-RPC 2.0 protocol implementation in the Dashboard and Daemon components.

## Table of Contents
1. [Basic Message Building](#basic-message-building)
2. [Message Parsing](#message-parsing)
3. [Dashboard WebSocket Handler](#dashboard-websocket-handler)
4. [Daemon WebSocket Client](#daemon-websocket-client)
5. [Error Handling Patterns](#error-handling-patterns)
6. [Thread-Safe Request Tracking](#thread-safe-request-tracking)

---

## Basic Message Building

### Building a Request (expects response)

```python
from backend.protocol import build_request

# Auto-incrementing ID
request = build_request("container.start", {
    "model": "llama-70b-Q4_K_M",
    "runtime": "vllm",
    "gpus": [0, 1],
    "config": {
        "context_length": 4096,
        "max_parallel": 32
    }
})

# Result:
# {
#     "jsonrpc": "2.0",
#     "method": "container.start",
#     "params": {...},
#     "id": 1
# }

# Custom ID
request = build_request("ping", request_id="custom-123")
```

### Building a Notification (no response expected)

```python
from backend.protocol import build_notification

# Send stats report (daemon -> dashboard)
notification = build_notification("stats.report", {
    "machine_id": "gpu-server-b",
    "timestamp": "2025-12-24T10:00:00Z",
    "cpu": {
        "cores": 32,
        "load_percent": 45.2
    },
    "memory": {
        "total_gb": 128.0,
        "used_gb": 64.3,
        "available_gb": 63.7
    },
    "gpus": [
        {
            "index": 0,
            "uuid": "GPU-...",
            "memory_used_mb": 12288,
            "utilization_percent": 85.0
        }
    ]
})

# Result:
# {
#     "jsonrpc": "2.0",
#     "method": "stats.report",
#     "params": {...}
# }
# Note: No "id" field
```

### Building a Success Response

```python
from backend.protocol import build_response

# Respond to container.start request
response = build_response(
    result={
        "container_id": "abc123",
        "status": "starting",
        "assigned_gpus": [0, 1]
    },
    request_id=1
)

# Result:
# {
#     "jsonrpc": "2.0",
#     "result": {...},
#     "id": 1
# }
```

### Building an Error Response

```python
from backend.protocol import build_error_response, ErrorCode

# Method not found
error = build_error_response(
    code=ErrorCode.METHOD_NOT_FOUND,
    message="Method not found",
    request_id=1
)

# Internal error with details
error = build_error_response(
    code=ErrorCode.INTERNAL_ERROR,
    message="Failed to start container",
    request_id=1,
    data={
        "reason": "Insufficient GPU memory",
        "available_mb": 2048,
        "required_mb": 24576
    }
)

# Parse error (no request ID)
error = build_error_response(
    code=ErrorCode.PARSE_ERROR,
    message="Invalid JSON",
    request_id=None,
    data="Unexpected end of JSON input"
)
```

---

## Message Parsing

### Basic Parsing

```python
from backend.protocol import (
    parse_message,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCErrorResponse,
)

# Parse from JSON string
raw_message = '{"jsonrpc": "2.0", "method": "ping", "id": 1}'
message = parse_message(raw_message)

# Parse from bytes
raw_bytes = b'{"jsonrpc": "2.0", "method": "stats.report"}'
message = parse_message(raw_bytes)

# Parse from dict (already parsed JSON)
raw_dict = {"jsonrpc": "2.0", "result": "pong", "id": 1}
message = parse_message(raw_dict)
```

### Type Discrimination

```python
from backend.protocol import parse_message, JSONRPCRequest

message = parse_message(raw_message)

# Pattern 1: Type checking
if isinstance(message, JSONRPCRequest):
    print(f"Request: {message.method}")
    print(f"Params: {message.params}")
    print(f"ID: {message.id}")

elif isinstance(message, JSONRPCNotification):
    print(f"Notification: {message.method}")
    # No response needed

elif isinstance(message, JSONRPCResponse):
    print(f"Response: {message.result}")
    print(f"Request ID: {message.id}")

elif isinstance(message, JSONRPCErrorResponse):
    print(f"Error {message.error.code}: {message.error.message}")
    if message.error.data:
        print(f"Details: {message.error.data}")
```

### Handling Parse Errors

```python
from backend.protocol import parse_message, JSONRPCErrorResponse, ErrorCode

# Invalid JSON
message = parse_message('{"invalid json')
assert isinstance(message, JSONRPCErrorResponse)
assert message.error.code == ErrorCode.PARSE_ERROR

# Invalid JSON-RPC structure
message = parse_message('{"foo": "bar"}')
assert isinstance(message, JSONRPCErrorResponse)
assert message.error.code == ErrorCode.INVALID_REQUEST
```

---

## Dashboard WebSocket Handler

### Complete Example

```python
from fastapi import WebSocket, WebSocketDisconnect
from backend.protocol import (
    parse_message,
    build_response,
    build_error_response,
    build_notification,
    JSONRPCRequest,
    JSONRPCNotification,
    JSONRPCErrorResponse,
    ErrorCode,
)
import structlog

logger = structlog.get_logger()

@app.websocket("/ws/daemon")
async def daemon_websocket(websocket: WebSocket):
    """WebSocket endpoint for daemon connections."""
    await websocket.accept()
    machine_id = None

    try:
        async for raw_message in websocket.iter_json():
            # Parse the JSON-RPC message
            message = parse_message(raw_message)

            # If parsing failed, send error and close
            if isinstance(message, JSONRPCErrorResponse):
                await websocket.send_json(message.model_dump())
                await websocket.close()
                return

            # Handle registration (first message must be daemon.register)
            if machine_id is None:
                if not isinstance(message, JSONRPCNotification):
                    error = build_error_response(
                        ErrorCode.INVALID_REQUEST,
                        "First message must be daemon.register notification",
                        message.id if hasattr(message, 'id') else None
                    )
                    await websocket.send_json(error)
                    await websocket.close()
                    return

                if message.method != "daemon.register":
                    error = build_error_response(
                        ErrorCode.INVALID_REQUEST,
                        "First message must be daemon.register",
                        None
                    )
                    await websocket.send_json(error)
                    await websocket.close()
                    return

                # Extract machine_id from registration
                machine_id = message.params["machine_id"]
                logger.info("daemon_registered", machine_id=machine_id)

                # Register in DaemonManager
                daemon_manager.register(machine_id, websocket)
                continue

            # Handle notifications
            if isinstance(message, JSONRPCNotification):
                await handle_notification(machine_id, message)

            # Handle requests (expect response)
            elif isinstance(message, JSONRPCRequest):
                response = await handle_request(machine_id, message)
                await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info("daemon_disconnected", machine_id=machine_id)
        if machine_id:
            daemon_manager.unregister(machine_id)


async def handle_notification(machine_id: str, message: JSONRPCNotification):
    """Handle notification from daemon."""
    if message.method == "stats.report":
        # Store stats to TimescaleDB
        await stats_storage.store(machine_id, message.params)
        # Update in-memory cluster state
        await cluster_state.update_machine_stats(machine_id, message.params)

    elif message.method == "container.status":
        # Update container status
        await cluster_state.update_container_status(
            machine_id,
            message.params["container_id"],
            message.params["status"]
        )

    else:
        logger.warning(
            "unknown_notification_method",
            method=message.method,
            machine_id=machine_id
        )


async def handle_request(machine_id: str, message: JSONRPCRequest) -> dict:
    """Handle request from daemon (return response)."""
    try:
        if message.method == "ping":
            return build_response("pong", message.id)

        else:
            return build_error_response(
                ErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {message.method}",
                message.id
            )

    except Exception as e:
        logger.exception("request_handler_error", method=message.method)
        return build_error_response(
            ErrorCode.INTERNAL_ERROR,
            str(e),
            message.id
        )
```

---

## Daemon WebSocket Client

### Complete Example

```python
import asyncio
import structlog
from websockets import connect, ConnectionClosed
from src.protocol import (
    build_request,
    build_notification,
    build_response,
    build_error_response,
    parse_message,
    JSONRPCRequest,
    JSONRPCResponse,
    ErrorCode,
)

logger = structlog.get_logger()


class WebSocketClient:
    """WebSocket client for daemon to connect to dashboard."""

    def __init__(self, dashboard_url: str, machine_id: str):
        self.dashboard_url = dashboard_url
        self.machine_id = machine_id
        self.websocket = None
        self.connected = False

    async def connect(self):
        """Connect to dashboard and maintain connection with reconnection."""
        backoff = 1.0
        max_backoff = 60.0

        while True:
            try:
                logger.info("connecting_to_dashboard", url=self.dashboard_url)
                async with connect(self.dashboard_url) as websocket:
                    self.websocket = websocket
                    self.connected = True
                    backoff = 1.0  # Reset backoff on successful connection

                    # Send registration
                    await self._send_registration()

                    # Handle messages
                    await self._message_loop()

            except ConnectionClosed:
                logger.warning("connection_closed", backoff=backoff)
                self.connected = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

            except Exception as e:
                logger.exception("connection_error", error=str(e))
                self.connected = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def _send_registration(self):
        """Send daemon.register notification."""
        # Collect initial stats
        stats = await stats_collector.collect()

        # Build registration notification
        registration = build_notification("daemon.register", {
            "machine_id": self.machine_id,
            "hostname": stats["hostname"],
            "stats": stats
        })

        await self.websocket.send_json(registration)
        logger.info("registration_sent", machine_id=self.machine_id)

    async def _message_loop(self):
        """Handle incoming messages from dashboard."""
        async for raw_message in self.websocket:
            message = parse_message(raw_message)

            # Handle requests (send response)
            if isinstance(message, JSONRPCRequest):
                response = await self._handle_request(message)
                await self.websocket.send_json(response)

            # Handle responses (match to pending requests)
            elif isinstance(message, JSONRPCResponse):
                # Handled by DaemonManager in real implementation
                logger.debug("response_received", id=message.id)

    async def _handle_request(self, message: JSONRPCRequest) -> dict:
        """Handle incoming request from dashboard."""
        try:
            if message.method == "container.start":
                result = await container_manager.start(message.params)
                return build_response(result, message.id)

            elif message.method == "container.stop":
                result = await container_manager.stop(message.params)
                return build_response(result, message.id)

            elif message.method == "ping":
                return build_response("pong", message.id)

            else:
                return build_error_response(
                    ErrorCode.METHOD_NOT_FOUND,
                    f"Method not found: {message.method}",
                    message.id
                )

        except Exception as e:
            logger.exception("request_handler_error", method=message.method)
            return build_error_response(
                ErrorCode.INTERNAL_ERROR,
                str(e),
                message.id,
                data={"traceback": traceback.format_exc()}
            )

    async def send_notification(self, method: str, params: dict):
        """Send notification to dashboard."""
        if not self.connected:
            logger.warning("not_connected_skipping_notification")
            return

        notification = build_notification(method, params)
        await self.websocket.send_json(notification)

    async def send_request(self, method: str, params: dict, timeout: float = 30.0):
        """Send request and wait for response."""
        if not self.connected:
            raise RuntimeError("Not connected to dashboard")

        request = build_request(method, params)
        request_id = request["id"]

        # Send request
        await self.websocket.send_json(request)

        # Wait for response (simplified - real implementation uses Future)
        # In real implementation, this would use DaemonManager's pending requests
        return await self._wait_for_response(request_id, timeout)
```

### Stats Reporting Loop

```python
async def stats_reporting_loop(websocket_client: WebSocketClient):
    """Background task to report stats every 6 seconds."""
    while True:
        try:
            # Collect stats
            stats = await stats_collector.collect()

            # Send as notification
            await websocket_client.send_notification("stats.report", stats)

            logger.debug("stats_reported")

        except Exception as e:
            logger.exception("stats_collection_error", error=str(e))

        # Wait 6 seconds
        await asyncio.sleep(6.0)
```

---

## Error Handling Patterns

### Graceful Error Handling

```python
from backend.protocol import parse_message, JSONRPCErrorResponse

# The parser NEVER raises exceptions - it returns error responses
message = parse_message('{"totally": "broken"}')

if isinstance(message, JSONRPCErrorResponse):
    # Handle the error gracefully
    logger.error(
        "invalid_message_received",
        error_code=message.error.code,
        error_message=message.error.message,
        error_data=message.error.data
    )
    # Optionally send error back to client
    await websocket.send_json(message.model_dump())
else:
    # Process valid message
    await handle_message(message)
```

### Request Handler Error Wrapping

```python
async def safe_handle_request(message: JSONRPCRequest) -> dict:
    """Safely handle request, catching all errors."""
    try:
        # Your request handling logic
        result = await process_request(message.method, message.params)
        return build_response(result, message.id)

    except ValueError as e:
        # Invalid parameters
        return build_error_response(
            ErrorCode.INVALID_PARAMS,
            str(e),
            message.id
        )

    except NotImplementedError:
        # Method exists but not implemented
        return build_error_response(
            ErrorCode.METHOD_NOT_FOUND,
            f"Method not implemented: {message.method}",
            message.id
        )

    except Exception as e:
        # Any other error
        logger.exception("request_error")
        return build_error_response(
            ErrorCode.INTERNAL_ERROR,
            "Internal error",
            message.id,
            data=str(e)
        )
```

---

## Thread-Safe Request Tracking

### DaemonManager with Pending Requests

```python
import asyncio
from typing import Dict, Optional
from backend.protocol import build_request, parse_message, JSONRPCResponse

class DaemonManager:
    """Manages daemon connections and pending requests."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.pending_requests: Dict[int, asyncio.Future] = {}

    async def send_request(
        self,
        machine_id: str,
        method: str,
        params: dict,
        timeout: float = 30.0
    ) -> dict:
        """Send request to daemon and wait for response."""
        # Get daemon connection
        websocket = self.connections.get(machine_id)
        if not websocket:
            raise ValueError(f"Daemon not connected: {machine_id}")

        # Build request (auto-incremented ID - thread-safe)
        request = build_request(method, params)
        request_id = request["id"]

        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        try:
            # Send request
            await websocket.send_json(request)

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            return response

        except asyncio.TimeoutError:
            raise TimeoutError(f"Request {request_id} timed out")

        finally:
            # Clean up
            self.pending_requests.pop(request_id, None)

    async def handle_response(self, raw_message: dict):
        """Handle response from daemon."""
        message = parse_message(raw_message)

        if not isinstance(message, JSONRPCResponse):
            return

        # Find pending request
        future = self.pending_requests.get(message.id)
        if future and not future.done():
            future.set_result(message.result)
```

### Usage Example

```python
# In WebSocket handler
daemon_manager = DaemonManager()

# Send command to daemon
try:
    result = await daemon_manager.send_request(
        machine_id="gpu-server-b",
        method="container.start",
        params={
            "model": "llama-70b-Q4_K_M",
            "runtime": "vllm",
            "gpus": [0, 1]
        },
        timeout=30.0
    )
    print(f"Container started: {result}")

except TimeoutError:
    print("Request timed out")

except ValueError as e:
    print(f"Error: {e}")
```

---

## Summary

The JSON-RPC 2.0 protocol implementation provides:

✅ **Type-safe message building** - Build requests, responses, notifications, and errors with full type hints

✅ **Robust parsing** - Parse any message format and get back a typed object (never raises exceptions)

✅ **Thread-safe ID generation** - Auto-incrementing request IDs that are safe for concurrent use

✅ **Standard error codes** - Pre-defined error codes matching the JSON-RPC 2.0 spec

✅ **Graceful error handling** - All errors are returned as proper JSON-RPC error responses

✅ **WebSocket integration** - Easy to integrate with FastAPI WebSocket handlers and websockets client

These examples demonstrate how the protocol layer integrates seamlessly with the Phase 4 WebSocket communication architecture.
