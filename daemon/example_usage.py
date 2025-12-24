#!/usr/bin/env python3
"""Example usage of the configuration and logging modules."""

import os

# Set required environment variable before import
os.environ["DASHBOARD_URL"] = "ws://dashboard.example.com:8080/ws/daemon"

# Optional: customize other settings
os.environ["MACHINE_ID"] = "gpu-node-example"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["LOG_FORMAT"] = "json"
os.environ["STATS_INTERVAL_SECONDS"] = "10"

# Now import the modules
from src import config, logger


def main():
    """Demonstrate configuration and logging usage."""
    # Log startup
    logger.info(
        "daemon_starting",
        machine_id=config.MACHINE_ID,
        dashboard_url=config.DASHBOARD_URL
    )

    # Display configuration
    logger.info(
        "configuration_loaded",
        proc_path=str(config.PROC_PATH),
        sys_path=str(config.SYS_PATH),
        podman_socket=str(config.PODMAN_SOCKET),
        model_path=str(config.MODEL_PATH),
        stats_interval=config.STATS_INTERVAL_SECONDS,
        health_check_interval=config.HEALTH_CHECK_INTERVAL_SECONDS,
        log_level=config.LOG_LEVEL,
        log_format=config.LOG_FORMAT
    )

    # Example of different log levels
    logger.debug("debug_message", detail="This is a debug message")
    logger.info("info_message", detail="This is an info message")
    logger.warning("warning_message", detail="This is a warning")
    logger.error("error_message", detail="This is an error", error_code=500)

    # Example with structured context
    logger.info(
        "stats_collected",
        cpu_load=45.2,
        memory_used_gb=32.5,
        gpu_count=2,
        gpu_utilization=[85, 92]
    )

    logger.info("daemon_ready", status="ready")


if __name__ == "__main__":
    main()
