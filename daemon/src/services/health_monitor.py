"""Health Monitor Service - Monitors container health and handles crashes."""

import asyncio
from datetime import datetime
from typing import Optional

import httpx
from podman.domain.containers import Container
from podman.errors import APIError

from src.config import config
from src.logger import logger
from src.services.container_manager import ContainerManager


class HealthMonitor:
    """
    Monitors health of running LLM containers.

    This service handles:
    - Periodic health checks via HTTP /health endpoint
    - Detection of crashed containers
    - Cleanup of failed containers
    - Tracking of containers in eviction state

    Health check logic:
    - Containers < 30s old: Status "starting" (no HTTP check)
    - Containers >= 30s old: HTTP GET to /health endpoint
    - Containers with status != "running": Status "crashed"
    """

    def __init__(
        self,
        container_manager: ContainerManager,
        websocket_client: Optional[object] = None,
    ) -> None:
        """
        Initialize the HealthMonitor.

        Args:
            container_manager: ContainerManager instance for managing containers
            websocket_client: Optional WebSocket client for notifications (Phase 4)
        """
        self.container_manager = container_manager
        self.websocket_client = websocket_client

        # Health check interval from config (default: 5 seconds)
        self.health_check_interval = config.HEALTH_CHECK_INTERVAL_SECONDS

        # Track containers in special states
        self.containers_starting: set[str] = set()
        self.containers_evicting: set[str] = set()

        logger.info(
            "HealthMonitor initialized",
            health_check_interval=self.health_check_interval,
        )

    def _container_age_seconds(self, container: Container) -> int:
        """
        Calculate the age of a container in seconds.

        Args:
            container: Container instance to check

        Returns:
            Age in seconds since container started, or 0 if unable to determine
        """
        try:
            # Get container attributes
            if not hasattr(container, 'attrs') or not container.attrs:
                logger.debug(
                    "Container missing attrs",
                    container_id=container.id[:12],
                )
                return 0

            # Extract StartedAt timestamp from State
            state = container.attrs.get("State", {})
            started_at_str = state.get("StartedAt")

            if not started_at_str:
                logger.debug(
                    "Container missing StartedAt timestamp",
                    container_id=container.id[:12],
                )
                return 0

            # Parse ISO timestamp
            started_at = datetime.fromisoformat(
                started_at_str.replace("Z", "+00:00")
            )

            # Calculate age
            age_seconds = int(
                (datetime.now(started_at.tzinfo) - started_at).total_seconds()
            )

            return age_seconds

        except Exception as e:
            logger.warning(
                "Failed to calculate container age",
                container_id=container.id[:12],
                error=str(e),
            )
            return 0

    async def check_container_health(self, container: Container) -> str:
        """
        Check the health status of a single container.

        Args:
            container: Container instance to check

        Returns:
            Health status: "healthy", "unhealthy", "starting", or "crashed"
        """
        try:
            # Reload container to get current status
            container.reload()

            # Check if container has crashed (not running)
            if container.status != "running":
                logger.debug(
                    "Container not running",
                    container_id=container.id[:12],
                    status=container.status,
                )
                return "crashed"

            # Get container age
            age_seconds = self._container_age_seconds(container)

            # Containers less than 30 seconds old are still starting
            if age_seconds < 30:
                logger.debug(
                    "Container still starting",
                    container_id=container.id[:12],
                    age_seconds=age_seconds,
                )
                return "starting"

            # For containers >= 30s old, perform HTTP health check
            # Get the port mapping for this container
            port_mappings = container.ports.get("8000/tcp")
            if not port_mappings or len(port_mappings) == 0:
                logger.warning(
                    "No port mapping found for health check",
                    container_id=container.id[:12],
                )
                return "unhealthy"

            host_port = port_mappings[0].get("HostPort")
            if not host_port:
                logger.warning(
                    "HostPort not found for health check",
                    container_id=container.id[:12],
                )
                return "unhealthy"

            # Perform HTTP health check with 5 second timeout
            health_url = f"http://localhost:{host_port}/health"

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(health_url, timeout=5.0)

                    if response.status_code == 200:
                        logger.debug(
                            "Health check passed",
                            container_id=container.id[:12],
                            age_seconds=age_seconds,
                        )
                        return "healthy"
                    else:
                        logger.warning(
                            "Health check failed with non-200 status",
                            container_id=container.id[:12],
                            status_code=response.status_code,
                        )
                        return "unhealthy"

                except httpx.TimeoutException:
                    logger.warning(
                        "Health check timed out",
                        container_id=container.id[:12],
                        timeout=5.0,
                    )
                    return "unhealthy"

                except httpx.RequestError as e:
                    logger.warning(
                        "Health check request failed",
                        container_id=container.id[:12],
                        error=str(e),
                    )
                    return "unhealthy"

        except APIError as e:
            logger.error(
                "Podman API error during health check",
                container_id=container.id[:12],
                error=str(e),
            )
            return "crashed"

        except Exception as e:
            logger.error(
                "Unexpected error during health check",
                container_id=container.id[:12],
                error=str(e),
            )
            return "unhealthy"

    async def check_all_containers(self) -> None:
        """
        Check health of all running containers.

        Iterates through all running containers and performs health checks.
        Handles crashes by calling handle_crash().
        Skips containers that are being evicted.
        """
        # Get snapshot of running containers
        containers_snapshot = list(self.container_manager.running_containers.items())

        for model_quant, container in containers_snapshot:
            # Skip containers that are being evicted
            if model_quant in self.containers_evicting:
                logger.debug(
                    "Skipping health check for evicting container",
                    model=model_quant,
                    container_id=container.id[:12],
                )
                continue

            try:
                # Perform health check
                health_status = await self.check_container_health(container)

                # Handle crashed containers
                if health_status == "crashed":
                    await self.handle_crash(model_quant, container)

            except Exception as e:
                logger.error(
                    "Error checking container health",
                    model=model_quant,
                    container_id=container.id[:12],
                    error=str(e),
                )

    async def handle_crash(self, model_quant: str, container: Container) -> None:
        """
        Handle a crashed container.

        Phase 2 implementation:
        - Logs the crash
        - Removes the crashed container
        - Cleans up tracking state

        Phase 4 will add:
        - WebSocket notification to dashboard
        - Automatic restart with stored configuration

        Args:
            model_quant: Model quantization identifier
            container: Crashed container instance
        """
        logger.warning(
            "Container crashed, cleaning up",
            model=model_quant,
            container_id=container.id[:12],
        )

        # Phase 2: Just log and clean up
        # Phase 4: Will send WebSocket notification and restart

        try:
            # Force remove the crashed container
            container.remove(force=True)

            # Remove from running containers tracking
            if model_quant in self.container_manager.running_containers:
                del self.container_manager.running_containers[model_quant]

            logger.info(
                "Crashed container removed",
                model=model_quant,
                container_id=container.id[:12],
            )

            # Phase 4: Will attempt restart here
            # stored_config = self._get_stored_config(model_quant)
            # if stored_config:
            #     await self.container_manager.start_container(stored_config)

        except Exception as e:
            logger.error(
                "Failed to remove crashed container",
                model=model_quant,
                container_id=container.id[:12],
                error=str(e),
            )

    def _get_stored_config(self, model_quant: str) -> Optional[object]:
        """
        Get stored configuration for a model.

        Phase 2: Stub implementation (returns None)
        Phase 4: Will retrieve configuration from persistent storage

        Args:
            model_quant: Model quantization identifier

        Returns:
            Stored ContainerConfig or None if not found
        """
        # Phase 2: No persistent storage yet
        # Phase 4: Will load from database/state store
        return None

    def mark_evicting(self, model_quant: str) -> None:
        """
        Mark a container as being evicted.

        Containers marked as evicting will be skipped during health checks
        to avoid false positives during the eviction process.

        Args:
            model_quant: Model quantization identifier
        """
        self.containers_evicting.add(model_quant)
        logger.debug(
            "Container marked as evicting",
            model=model_quant,
        )

    def unmark_evicting(self, model_quant: str) -> None:
        """
        Remove eviction mark from a container.

        Args:
            model_quant: Model quantization identifier
        """
        self.containers_evicting.discard(model_quant)
        logger.debug(
            "Container unmarked as evicting",
            model=model_quant,
        )

    async def run(self) -> None:
        """
        Run the health monitoring loop.

        Continuously checks container health at configured intervals.
        This method runs indefinitely until cancelled.
        """
        logger.info(
            "Starting health monitor loop",
            interval_seconds=self.health_check_interval,
        )

        try:
            while True:
                # Perform health checks on all containers
                await self.check_all_containers()

                # Wait for next check interval
                await asyncio.sleep(self.health_check_interval)

        except asyncio.CancelledError:
            logger.info("Health monitor loop cancelled")
            raise
        except Exception as e:
            logger.error(
                "Health monitor loop failed",
                error=str(e),
            )
            raise
