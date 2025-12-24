"""LLM Serve Daemon - Main Entrypoint.

This module initializes and runs all daemon services:
- StatsCollector: Collects CPU, memory, network, and GPU metrics
- ContainerManager: Manages LLM container lifecycle
- HealthMonitor: Monitors container health and handles crashes
- WebSocketClient: Connects to Dashboard and handles bidirectional communication

Phase 4: Full WebSocket integration with stats reporting and command handling
"""

import asyncio
import json
import signal
from typing import Optional

from src.config import config
from src.logger import logger
from src.services.stats_collector import StatsCollector
from src.services.container_manager import ContainerManager
from src.services.health_monitor import HealthMonitor
from src.services.websocket_client import WebSocketClient

# Global service instances
stats_collector: Optional[StatsCollector] = None
container_manager: Optional[ContainerManager] = None
health_monitor: Optional[HealthMonitor] = None
websocket_client: Optional[WebSocketClient] = None


def initialize_services() -> None:
    """Initialize all daemon services."""
    global stats_collector, container_manager, health_monitor, websocket_client

    logger.info(
        "initializing_services",
        machine_id=config.MACHINE_ID,
        dashboard_url=config.DASHBOARD_URL,
        proc_path=str(config.PROC_PATH),
        sys_path=str(config.SYS_PATH),
        podman_socket=str(config.PODMAN_SOCKET),
    )

    # Initialize ContainerManager first (needed by StatsCollector)
    container_manager = ContainerManager()
    logger.info("container_manager_initialized")

    # Initialize StatsCollector with host paths and container_manager
    stats_collector = StatsCollector(
        proc_path=str(config.PROC_PATH),
        sys_path=str(config.SYS_PATH),
        container_manager=container_manager,
    )
    logger.info("stats_collector_initialized")

    # Initialize WebSocketClient for Dashboard communication
    websocket_client = WebSocketClient(
        dashboard_url=config.DASHBOARD_URL,
        stats_collector=stats_collector,
        container_manager=container_manager,
    )
    logger.info("websocket_client_initialized")

    # Initialize HealthMonitor with websocket_client
    health_monitor = HealthMonitor(
        container_manager=container_manager,
        websocket_client=websocket_client,
    )
    logger.info("health_monitor_initialized")


async def stats_reporting_loop() -> None:
    """
    Periodic stats collection and reporting loop.

    Collects system metrics every STATS_INTERVAL_SECONDS and sends them
    to Dashboard via WebSocket.
    """
    global websocket_client

    logger.info(
        "stats_reporting_loop_starting",
        interval_seconds=config.STATS_INTERVAL_SECONDS,
    )

    while True:
        try:
            # Send stats report to Dashboard
            await websocket_client.send_stats_report()

        except Exception as e:
            logger.error("stats_reporting_failed", error=str(e))

        # Wait for next collection interval
        await asyncio.sleep(config.STATS_INTERVAL_SECONDS)


async def main() -> None:
    """
    Main entry point for the LLM Serve Daemon.

    Initializes all services and starts background tasks for:
    - WebSocket connection to Dashboard (with auto-reconnection)
    - Health monitoring
    - Stats reporting

    Phase 4: Full WebSocket integration with Dashboard communication
    """
    logger.info(
        "daemon_starting",
        machine_id=config.MACHINE_ID,
        dashboard_url=config.DASHBOARD_URL,
        stats_interval=config.STATS_INTERVAL_SECONDS,
        health_check_interval=config.HEALTH_CHECK_INTERVAL_SECONDS,
    )

    # Initialize all services
    initialize_services()

    # Create background tasks
    tasks = []

    # Start health monitor loop
    health_monitor_task = asyncio.create_task(health_monitor.run())
    health_monitor_task.set_name("health_monitor")
    tasks.append(health_monitor_task)
    logger.info("health_monitor_task_started")

    # Start stats reporting loop
    stats_reporting_task = asyncio.create_task(stats_reporting_loop())
    stats_reporting_task.set_name("stats_reporting")
    tasks.append(stats_reporting_task)
    logger.info("stats_reporting_task_started")

    logger.info("daemon_ready", machine_id=config.MACHINE_ID)

    # Phase 4: Connect to Dashboard and maintain connection
    # This is the main blocking task that runs until shutdown
    try:
        # Set up signal handlers for graceful shutdown
        shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        def signal_handler():
            logger.info("shutdown_signal_received")
            shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        # Start WebSocket connection task (runs until shutdown)
        websocket_task = asyncio.create_task(websocket_client.connect())
        websocket_task.set_name("websocket_client")
        tasks.append(websocket_task)
        logger.info("websocket_client_task_started")

        # Wait for shutdown signal
        await shutdown_event.wait()

    except asyncio.CancelledError:
        logger.info("daemon_cancelled")
    finally:
        # Cancel all background tasks
        logger.info("daemon_shutting_down")
        for task in tasks:
            task.cancel()

        # Wait for tasks to complete cancellation
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("daemon_stopped", machine_id=config.MACHINE_ID)


if __name__ == "__main__":
    asyncio.run(main())
