"""WebSocket handlers for daemon and UI client connections.

This module provides WebSocket endpoints for:
- Daemon connections (/ws/daemon) - bidirectional communication with GPU daemons
- UI client connections (/ws/ui) - real-time cluster state updates for web UI
"""

import asyncio
from typing import Any, Dict

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from dashboard.backend.services.cluster_state import cluster_state
from dashboard.backend.services.daemon_manager import daemon_manager
from dashboard.backend.services.stats_storage import stats_storage
from dashboard.backend.services.ui_manager import ui_manager

logger = structlog.get_logger(__name__)

# Create router for WebSocket endpoints
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/daemon")
async def websocket_daemon_endpoint(websocket: WebSocket):
    """WebSocket endpoint for daemon connections.

    Accepts connections from GPU server daemons, handles registration,
    receives stats reports, and sends commands.

    Protocol: JSON-RPC 2.0
    First message must be: daemon.register notification
    """
    await websocket.accept()

    machine_id: str | None = None

    try:
        # Wait for registration message
        registration = await websocket.receive_json()

        # Validate registration
        if not _validate_registration(registration):
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid registration. First message must be daemon.register notification",
                },
            }
            await websocket.send_json(error_response)
            await websocket.close()
            return

        # Extract machine_id and hostname from registration
        params = registration.get("params", {})
        machine_id = params.get("machine_id")
        hostname = params.get("hostname", machine_id)

        if not machine_id:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "machine_id required in registration params",
                },
            }
            await websocket.send_json(error_response)
            await websocket.close()
            return

        # Register daemon
        await daemon_manager.register(machine_id, websocket)
        await cluster_state.mark_machine_online(machine_id, hostname)

        logger.info(
            "daemon_connected",
            machine_id=machine_id,
            hostname=hostname,
        )

        # Process initial stats if provided
        if "stats" in params:
            await _handle_stats_report(machine_id, params["stats"])

        # Message loop - handle incoming messages from daemon
        async for message in websocket.iter_json():
            await daemon_manager.update_last_seen(machine_id)

            # Log all incoming messages at debug level
            logger.debug(
                "daemon_message_received",
                machine_id=machine_id,
                method=message.get("method"),
                has_id="id" in message,
            )

            # Dispatch message to appropriate handler
            await _dispatch_daemon_message(machine_id, message)

    except WebSocketDisconnect:
        logger.info("daemon_disconnected", machine_id=machine_id)

    except Exception as e:
        logger.error(
            "daemon_websocket_error",
            machine_id=machine_id,
            error=str(e),
            error_type=type(e).__name__,
        )

    finally:
        # Clean up on disconnect
        if machine_id:
            await daemon_manager.unregister(machine_id)
            await cluster_state.mark_machine_offline(machine_id)


def _validate_registration(message: Dict[str, Any]) -> bool:
    """Validate daemon registration message.

    Args:
        message: Registration message

    Returns:
        True if valid registration, False otherwise
    """
    # Must be JSON-RPC 2.0
    if message.get("jsonrpc") != "2.0":
        return False

    # Must be daemon.register method
    if message.get("method") != "daemon.register":
        return False

    # Must be notification (no id)
    if "id" in message:
        return False

    # Must have params
    if "params" not in message:
        return False

    return True


async def _dispatch_daemon_message(machine_id: str, message: Dict[str, Any]) -> None:
    """Dispatch incoming daemon message to appropriate handler.

    Args:
        machine_id: Machine identifier
        message: JSON-RPC message
    """
    method = message.get("method")
    params = message.get("params", {})
    message_id = message.get("id")

    # Check if this is a response (has id and result/error)
    if message_id is not None and ("result" in message or "error" in message):
        # This is a response to a request we sent
        await daemon_manager.handle_response(message)
        return

    # Handle different message types
    if method == "stats.report":
        await _handle_stats_report(machine_id, params)

    elif method == "container.status":
        await _handle_container_status(machine_id, params)

    elif method:
        # Unknown method - send error response if this was a request
        if message_id is not None:
            error_response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }
            websocket = daemon_manager.get_websocket(machine_id)
            if websocket:
                await websocket.send_json(error_response)

        logger.warning(
            "unknown_daemon_method",
            machine_id=machine_id,
            method=method,
        )


async def _handle_stats_report(machine_id: str, stats: Dict[str, Any]) -> None:
    """Handle stats.report notification from daemon.

    Args:
        machine_id: Machine identifier
        stats: Stats dictionary
    """
    # Store stats to database asynchronously (don't block WebSocket)
    asyncio.create_task(stats_storage.store_stats(machine_id, stats))

    # Update in-memory cluster state
    await cluster_state.update_machine_stats(machine_id, stats)

    logger.debug(
        "stats_report_handled",
        machine_id=machine_id,
    )


async def _handle_container_status(machine_id: str, params: Dict[str, Any]) -> None:
    """Handle container.status notification from daemon.

    Args:
        machine_id: Machine identifier
        params: Status parameters
    """
    container_id = params.get("container_id")
    status = params.get("status")

    if not container_id or not status:
        logger.warning(
            "invalid_container_status",
            machine_id=machine_id,
            params=params,
        )
        return

    # Update cluster state
    await cluster_state.update_container_status(machine_id, container_id, status)

    logger.debug(
        "container_status_handled",
        machine_id=machine_id,
        container_id=container_id,
        status=status,
    )


@router.websocket("/ws/ui")
async def websocket_ui_endpoint(websocket: WebSocket):
    """WebSocket endpoint for UI client connections.

    Accepts connections from web UI clients and sends real-time
    cluster state updates.

    Initial message: Full cluster state snapshot
    Subsequent messages: State change notifications
    """
    await websocket.accept()

    try:
        # Add client to manager
        await ui_manager.add_client(websocket)

        logger.info("ui_client_connected")

        # Send initial cluster state snapshot
        machines = await cluster_state.get_all_machines()
        status = cluster_state.get_status()

        # Convert dataclasses to dicts for JSON serialization
        machines_dict = {
            machine_id: {
                "machine_id": machine.machine_id,
                "hostname": machine.hostname,
                "connected": machine.connected,
                "last_seen": machine.last_seen.isoformat() if machine.last_seen else None,
                "cpu_model": machine.cpu_model,
                "cpu_cores": machine.cpu_cores,
                "cpu_load_percent": machine.cpu_load_percent,
                "memory_total_gb": machine.memory_total_gb,
                "memory_used_gb": machine.memory_used_gb,
                "memory_available_gb": machine.memory_available_gb,
                "gpus": [
                    {
                        "gpu_index": gpu.gpu_index,
                        "gpu_uuid": gpu.gpu_uuid,
                        "gpu_name": gpu.gpu_name,
                        "memory_total_gb": gpu.memory_total_gb,
                        "memory_used_gb": gpu.memory_used_gb,
                        "utilization": gpu.utilization,
                        "temperature_c": gpu.temperature_c,
                        "assigned_model": gpu.assigned_model,
                    }
                    for gpu in machine.gpus
                ],
                "containers": [
                    {
                        "container_id": container.container_id,
                        "model": container.model,
                        "runtime": container.runtime,
                        "gpus": container.gpus,
                        "status": container.status,
                        "uptime": container.uptime,
                    }
                    for container in machine.containers
                ],
            }
            for machine_id, machine in machines.items()
        }

        initial_state = {
            "type": "initial_state",
            "data": {
                "machines": machines_dict,
                "status": {
                    "total_machines": status.total_machines,
                    "online_machines": status.online_machines,
                    "total_gpus": status.total_gpus,
                    "free_gpus": status.free_gpus,
                    "running_models": status.running_models,
                },
            },
        }
        await websocket.send_json(initial_state)

        # Keep connection alive - wait for disconnect or incoming messages
        # UI clients typically only receive, but we handle incoming messages
        # for potential future features (e.g., client-side filtering)
        while True:
            try:
                # Wait for message with timeout to send periodic pings
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0,
                )

                # Handle any incoming messages (currently unused)
                logger.debug("ui_message_received", message=message)

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        logger.info("ui_client_disconnected")

    except Exception as e:
        logger.error(
            "ui_websocket_error",
            error=str(e),
            error_type=type(e).__name__,
        )

    finally:
        # Remove client on disconnect
        await ui_manager.remove_client(websocket)
