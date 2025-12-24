"""LLM Serve Daemon - Main Entrypoint.

This module initializes and runs all daemon services:
- StatsCollector: Collects CPU, memory, network, and GPU metrics
- ContainerManager: Manages LLM container lifecycle
- HealthMonitor: Monitors container health and handles crashes

Phase 2: Stats are printed to stdout (WebSocket integration in Phase 4)
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

# Global service instances
stats_collector: Optional[StatsCollector] = None
container_manager: Optional[ContainerManager] = None
health_monitor: Optional[HealthMonitor] = None


def initialize_services() -> None:
    """Initialize all daemon services."""
    global stats_collector, container_manager, health_monitor

    logger.info(
        "initializing_services",
        machine_id=config.MACHINE_ID,
        proc_path=str(config.PROC_PATH),
        sys_path=str(config.SYS_PATH),
        podman_socket=str(config.PODMAN_SOCKET),
    )

    # Initialize StatsCollector with host paths
    stats_collector = StatsCollector(
        proc_path=str(config.PROC_PATH),
        sys_path=str(config.SYS_PATH),
    )
    logger.info("stats_collector_initialized")

    # Initialize ContainerManager with Podman socket
    container_manager = ContainerManager()
    logger.info("container_manager_initialized")

    # Initialize HealthMonitor (websocket_client=None for Phase 2)
    health_monitor = HealthMonitor(
        container_manager=container_manager,
        websocket_client=None,  # Will be set in Phase 4
    )
    logger.info("health_monitor_initialized")


async def stats_loop() -> None:
    """
    Periodic stats collection and output loop.

    Collects system metrics every STATS_INTERVAL_SECONDS and outputs
    them to stdout as JSON. In Phase 4, this will send via WebSocket.
    """
    global stats_collector

    logger.info(
        "stats_loop_starting",
        interval_seconds=config.STATS_INTERVAL_SECONDS,
    )

    while True:
        try:
            # Collect stats
            stats = await stats_collector.collect()

            # Phase 2: Print stats to stdout as JSON
            # Phase 4: Will send via WebSocket to Dashboard
            stats_json = json.dumps(stats.to_dict(), indent=2)
            print(stats_json)

            logger.debug(
                "stats_collected",
                gpu_count=len(stats.gpus),
                container_count=len(stats.containers),
                cpu_load=stats.cpu.load_percent,
                memory_used_gb=stats.memory.used_gb,
            )

        except Exception as e:
            logger.error("stats_collection_failed", error=str(e))

        # Wait for next collection interval
        await asyncio.sleep(config.STATS_INTERVAL_SECONDS)


async def main() -> None:
    """
    Main entry point for the LLM Serve Daemon.

    Initializes all services and starts background tasks for:
    - Health monitoring
    - Stats collection

    In Phase 4, will also connect to Dashboard via WebSocket.
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

    # Start stats collection loop
    stats_loop_task = asyncio.create_task(stats_loop())
    stats_loop_task.set_name("stats_loop")
    tasks.append(stats_loop_task)
    logger.info("stats_loop_task_started")

    logger.info("daemon_ready", machine_id=config.MACHINE_ID)

    # Phase 4: Will await websocket_client.connect() here
    # For Phase 2, keep main coroutine alive with Event.wait()
    try:
        shutdown_event = asyncio.Event()

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: shutdown_event.set())

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
