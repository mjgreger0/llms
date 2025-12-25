"""Container health checker service.

Polls container health endpoints to determine when containers are ready
to receive requests after startup.
"""

import asyncio
from typing import Tuple

import httpx
import structlog

logger = structlog.get_logger(__name__)


class ContainerHealthChecker:
    """Async service for polling container health endpoints.

    Provides methods to check container health status and poll until
    containers are ready to serve requests.
    """

    def __init__(self):
        """Initialize the health checker."""
        self._http_client: httpx.AsyncClient | None = None
        logger.info("container_health_checker_initialized")

    async def startup(self):
        """Initialize HTTP client on startup."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                follow_redirects=True,
            )
            logger.info("health_checker_started")

    async def shutdown(self):
        """Clean up HTTP client on shutdown."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("health_checker_shutdown")

    async def check_once(self, endpoint: str) -> Tuple[bool, int]:
        """Perform a single health check on the endpoint.

        Args:
            endpoint: Base URL of the container (e.g., "http://localhost:8000")

        Returns:
            Tuple of (success: bool, status_code: int)
            Success is True if status code is 200, False otherwise.
            Status code is 0 if connection failed.

        Examples:
            >>> checker = ContainerHealthChecker()
            >>> await checker.startup()
            >>> success, code = await checker.check_once("http://localhost:8000")
            >>> print(f"Success: {success}, Code: {code}")
        """
        if self._http_client is None:
            await self.startup()

        health_url = f"{endpoint.rstrip('/')}/health"

        try:
            response = await self._http_client.get(health_url)
            success = response.status_code == 200

            logger.debug(
                "health_check_single",
                endpoint=endpoint,
                status_code=response.status_code,
                success=success,
            )

            return (success, response.status_code)

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.debug(
                "health_check_connection_error",
                endpoint=endpoint,
                error=str(e),
                error_type=type(e).__name__,
            )
            return (False, 0)

        except Exception as e:
            logger.warning(
                "health_check_unexpected_error",
                endpoint=endpoint,
                error=str(e),
                error_type=type(e).__name__,
            )
            return (False, 0)

    async def poll_until_ready(
        self,
        endpoint: str,
        timeout: float,
        interval: float = 1.0,
    ) -> bool:
        """Poll the health endpoint until it returns 200 OK or timeout.

        Args:
            endpoint: Base URL of the container (e.g., "http://localhost:8000")
            timeout: Maximum time to wait in seconds
            interval: Time between polling attempts in seconds (default: 1.0)

        Returns:
            True if health check succeeded within timeout

        Raises:
            TimeoutError: If timeout is exceeded before container becomes healthy

        Examples:
            >>> checker = ContainerHealthChecker()
            >>> await checker.startup()
            >>> # Wait up to 60 seconds for container to be ready
            >>> ready = await checker.poll_until_ready(
            ...     "http://localhost:8000",
            ...     timeout=60.0,
            ...     interval=2.0
            ... )
            >>> print(f"Container ready: {ready}")
        """
        if self._http_client is None:
            await self.startup()

        start_time = asyncio.get_event_loop().time()
        attempt = 0

        logger.info(
            "health_check_polling_started",
            endpoint=endpoint,
            timeout=timeout,
            interval=interval,
        )

        while True:
            attempt += 1
            elapsed = asyncio.get_event_loop().time() - start_time

            # Check if we've exceeded timeout
            if elapsed >= timeout:
                logger.error(
                    "health_check_timeout",
                    endpoint=endpoint,
                    timeout=timeout,
                    attempts=attempt,
                    elapsed=elapsed,
                )
                raise TimeoutError(
                    f"Container health check timed out after {timeout}s "
                    f"({attempt} attempts)"
                )

            # Perform health check
            success, status_code = await self.check_once(endpoint)

            logger.info(
                "container_health_check",
                endpoint=endpoint,
                status=status_code,
                attempt=attempt,
                elapsed=round(elapsed, 2),
            )

            if success:
                logger.info(
                    "health_check_succeeded",
                    endpoint=endpoint,
                    attempts=attempt,
                    elapsed=round(elapsed, 2),
                )
                return True

            # Wait before next attempt
            await asyncio.sleep(interval)

    def calculate_timeout_for_vram(self, vram_gb: float) -> float:
        """Calculate health check timeout based on model VRAM requirements.

        Args:
            vram_gb: VRAM requirement in GB

        Returns:
            Timeout in seconds

        Examples:
            >>> checker = ContainerHealthChecker()
            >>> checker.calculate_timeout_for_vram(10.0)  # Small model
            60
            >>> checker.calculate_timeout_for_vram(25.0)  # Medium model
            120
            >>> checker.calculate_timeout_for_vram(45.0)  # Large model
            180
            >>> checker.calculate_timeout_for_vram(80.0)  # XLarge model
            300
        """
        # Timeout tiers based on model size (VRAM as proxy)
        if vram_gb < 15:  # Small models
            timeout = 60
        elif vram_gb < 30:  # Medium models
            timeout = 120
        elif vram_gb < 70:  # Large models (>30GB VRAM)
            timeout = 180
        else:  # XLarge models (>70GB VRAM)
            timeout = 300

        logger.debug(
            "calculated_health_timeout",
            vram_gb=vram_gb,
            timeout=timeout,
        )

        return timeout


# Singleton instance
health_checker = ContainerHealthChecker()
