"""Unit tests for ContainerHealthChecker (Phase 7)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from dashboard.backend.services.health_check import ContainerHealthChecker


@pytest.fixture
def health_checker():
    """Create a fresh ContainerHealthChecker for each test."""
    return ContainerHealthChecker()


@pytest.fixture
async def started_health_checker():
    """Create and start a health checker."""
    checker = ContainerHealthChecker()
    await checker.startup()
    yield checker
    await checker.shutdown()


class TestHealthCheckerLifecycle:
    """Test health checker initialization and lifecycle."""

    @pytest.mark.asyncio
    async def test_startup_creates_http_client(self, health_checker):
        """Test that startup initializes the HTTP client."""
        assert health_checker._http_client is None

        await health_checker.startup()

        assert health_checker._http_client is not None
        assert isinstance(health_checker._http_client, httpx.AsyncClient)

        # Cleanup
        await health_checker.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_closes_http_client(self, health_checker):
        """Test that shutdown closes the HTTP client."""
        await health_checker.startup()
        assert health_checker._http_client is not None

        await health_checker.shutdown()

        assert health_checker._http_client is None

    @pytest.mark.asyncio
    async def test_startup_idempotent(self, health_checker):
        """Test that calling startup multiple times is safe."""
        await health_checker.startup()
        client1 = health_checker._http_client

        await health_checker.startup()
        client2 = health_checker._http_client

        # Should be the same client
        assert client1 is client2

        # Cleanup
        await health_checker.shutdown()


class TestCheckOnce:
    """Test single health check functionality."""

    @pytest.mark.asyncio
    async def test_check_once_success(self, started_health_checker):
        """Test successful health check returns (True, 200)."""
        endpoint = "http://localhost:8000"

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(
            started_health_checker._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            success, status_code = await started_health_checker.check_once(endpoint)

        assert success is True
        assert status_code == 200

    @pytest.mark.asyncio
    async def test_check_once_non_200_response(self, started_health_checker):
        """Test non-200 response returns (False, status_code)."""
        endpoint = "http://localhost:8000"

        # Mock 503 Service Unavailable
        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch.object(
            started_health_checker._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            success, status_code = await started_health_checker.check_once(endpoint)

        assert success is False
        assert status_code == 503

    @pytest.mark.asyncio
    async def test_check_once_connection_error(self, started_health_checker):
        """Test connection error returns (False, 0)."""
        endpoint = "http://localhost:8000"

        # Mock connection error
        with patch.object(
            started_health_checker._http_client,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            success, status_code = await started_health_checker.check_once(endpoint)

        assert success is False
        assert status_code == 0

    @pytest.mark.asyncio
    async def test_check_once_timeout_error(self, started_health_checker):
        """Test timeout error returns (False, 0)."""
        endpoint = "http://localhost:8000"

        # Mock timeout
        with patch.object(
            started_health_checker._http_client,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("Request timeout"),
        ):
            success, status_code = await started_health_checker.check_once(endpoint)

        assert success is False
        assert status_code == 0

    @pytest.mark.asyncio
    async def test_check_once_network_error(self, started_health_checker):
        """Test network error returns (False, 0)."""
        endpoint = "http://localhost:8000"

        # Mock network error
        with patch.object(
            started_health_checker._http_client,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.NetworkError("Network unreachable"),
        ):
            success, status_code = await started_health_checker.check_once(endpoint)

        assert success is False
        assert status_code == 0

    @pytest.mark.asyncio
    async def test_check_once_constructs_correct_url(self, started_health_checker):
        """Test that check_once appends /health to endpoint."""
        endpoint = "http://localhost:8000"
        expected_url = "http://localhost:8000/health"

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_get = AsyncMock(return_value=mock_response)

        with patch.object(started_health_checker._http_client, "get", mock_get):
            await started_health_checker.check_once(endpoint)

        # Verify the correct URL was called
        mock_get.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_check_once_strips_trailing_slash(self, started_health_checker):
        """Test that trailing slash is handled correctly."""
        endpoint = "http://localhost:8000/"
        expected_url = "http://localhost:8000/health"

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_get = AsyncMock(return_value=mock_response)

        with patch.object(started_health_checker._http_client, "get", mock_get):
            await started_health_checker.check_once(endpoint)

        mock_get.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_check_once_auto_starts_client(self, health_checker):
        """Test that check_once starts client if not already started."""
        assert health_checker._http_client is None

        mock_response = MagicMock()
        mock_response.status_code = 200

        # Patch the startup to set a mock client
        async def mock_startup():
            health_checker._http_client = MagicMock()
            health_checker._http_client.get = AsyncMock(return_value=mock_response)

        with patch.object(health_checker, "startup", side_effect=mock_startup):
            success, status_code = await health_checker.check_once(
                "http://localhost:8000"
            )

        assert success is True
        assert status_code == 200


class TestPollUntilReady:
    """Test polling functionality."""

    @pytest.mark.asyncio
    async def test_poll_succeeds_immediately(self, started_health_checker):
        """Test polling succeeds on first attempt."""
        endpoint = "http://localhost:8000"

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(
            started_health_checker._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await started_health_checker.poll_until_ready(
                endpoint, timeout=10.0, interval=1.0
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_poll_succeeds_after_retries(self, started_health_checker):
        """Test polling succeeds after several failed attempts."""
        endpoint = "http://localhost:8000"

        # First 3 attempts fail, 4th succeeds
        mock_responses = [
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            MagicMock(status_code=200),
        ]

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            response = mock_responses[call_count]
            call_count += 1
            if isinstance(response, Exception):
                raise response
            return response

        with patch.object(
            started_health_checker._http_client, "get", side_effect=mock_get
        ):
            result = await started_health_checker.poll_until_ready(
                endpoint, timeout=10.0, interval=0.1  # Short interval for testing
            )

        assert result is True
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_poll_timeout_raises_error(self, started_health_checker):
        """Test polling raises TimeoutError when timeout exceeded."""
        endpoint = "http://localhost:8000"

        # Always fail
        with patch.object(
            started_health_checker._http_client,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(TimeoutError) as exc_info:
                await started_health_checker.poll_until_ready(
                    endpoint, timeout=0.5, interval=0.1
                )

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_poll_respects_interval(self, started_health_checker):
        """Test that polling respects the interval parameter."""
        endpoint = "http://localhost:8000"
        interval = 0.2

        # Fail 3 times, then succeed
        mock_responses = [
            MagicMock(status_code=503),
            MagicMock(status_code=503),
            MagicMock(status_code=200),
        ]

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            response = mock_responses[call_count]
            call_count += 1
            return response

        start_time = asyncio.get_event_loop().time()

        with patch.object(
            started_health_checker._http_client, "get", side_effect=mock_get
        ):
            await started_health_checker.poll_until_ready(
                endpoint, timeout=10.0, interval=interval
            )

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have waited at least 2 * interval (between 3 attempts)
        assert elapsed >= 2 * interval

    @pytest.mark.asyncio
    async def test_poll_logs_attempts(self, started_health_checker):
        """Test that polling logs each attempt."""
        endpoint = "http://localhost:8000"

        # Fail once, then succeed
        mock_responses = [
            MagicMock(status_code=503),
            MagicMock(status_code=200),
        ]

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            response = mock_responses[call_count]
            call_count += 1
            return response

        with patch.object(
            started_health_checker._http_client, "get", side_effect=mock_get
        ):
            with patch("dashboard.backend.services.health_check.logger") as mock_logger:
                await started_health_checker.poll_until_ready(
                    endpoint, timeout=10.0, interval=0.1
                )

                # Should have logged polling started, each attempt, and success
                assert mock_logger.info.call_count >= 3

                # Check that "container_health_check" was logged
                log_calls = [
                    call[1] for call in mock_logger.info.call_args_list
                ]
                event_names = [call.get("event") if isinstance(call, dict) else call[0] for call in log_calls]
                assert "container_health_check" in event_names

    @pytest.mark.asyncio
    async def test_poll_auto_starts_client(self, health_checker):
        """Test that poll_until_ready starts client if not already started."""
        assert health_checker._http_client is None

        mock_response = MagicMock()
        mock_response.status_code = 200

        # Patch the startup to set a mock client
        async def mock_startup():
            health_checker._http_client = MagicMock()
            health_checker._http_client.get = AsyncMock(return_value=mock_response)

        with patch.object(health_checker, "startup", side_effect=mock_startup):
            result = await health_checker.poll_until_ready(
                "http://localhost:8000", timeout=10.0
            )

        assert result is True


class TestTimeoutCalculation:
    """Test timeout calculation based on VRAM requirements."""

    def test_calculate_timeout_small_model(self, health_checker):
        """Test timeout for small models (<15GB VRAM)."""
        timeout = health_checker.calculate_timeout_for_vram(10.0)
        assert timeout == 60

    def test_calculate_timeout_medium_model(self, health_checker):
        """Test timeout for medium models (15-30GB VRAM)."""
        timeout = health_checker.calculate_timeout_for_vram(20.0)
        assert timeout == 120

        timeout = health_checker.calculate_timeout_for_vram(25.0)
        assert timeout == 120

    def test_calculate_timeout_large_model(self, health_checker):
        """Test timeout for large models (30-70GB VRAM)."""
        timeout = health_checker.calculate_timeout_for_vram(40.0)
        assert timeout == 180

        timeout = health_checker.calculate_timeout_for_vram(60.0)
        assert timeout == 180

    def test_calculate_timeout_xlarge_model(self, health_checker):
        """Test timeout for xlarge models (>70GB VRAM)."""
        timeout = health_checker.calculate_timeout_for_vram(80.0)
        assert timeout == 300

        timeout = health_checker.calculate_timeout_for_vram(100.0)
        assert timeout == 300

    def test_calculate_timeout_boundary_values(self, health_checker):
        """Test timeout at boundary values."""
        # Just under 15GB should be small
        assert health_checker.calculate_timeout_for_vram(14.9) == 60

        # Exactly 15GB should be medium
        assert health_checker.calculate_timeout_for_vram(15.0) == 120

        # Just under 30GB should be medium
        assert health_checker.calculate_timeout_for_vram(29.9) == 120

        # Exactly 30GB should be large
        assert health_checker.calculate_timeout_for_vram(30.0) == 180

        # Just under 70GB should be large
        assert health_checker.calculate_timeout_for_vram(69.9) == 180

        # Exactly 70GB should be xlarge
        assert health_checker.calculate_timeout_for_vram(70.0) == 300


class TestSingletonInstance:
    """Test the singleton instance."""

    def test_singleton_exists(self):
        """Test that health_checker singleton is available."""
        from dashboard.backend.services.health_check import health_checker

        assert health_checker is not None
        assert isinstance(health_checker, ContainerHealthChecker)

    @pytest.mark.asyncio
    async def test_singleton_lifecycle(self):
        """Test singleton can be started and stopped."""
        from dashboard.backend.services.health_check import health_checker

        await health_checker.startup()
        assert health_checker._http_client is not None

        await health_checker.shutdown()
        assert health_checker._http_client is None
