"""Unit tests for QueueManager (Task 7.2)."""

import asyncio
from datetime import datetime, timedelta

import pytest

from dashboard.backend.services.queue_manager import QueueManager, RequestContext


@pytest.fixture
def queue_manager():
    """Create a fresh QueueManager for each test."""
    return QueueManager()


@pytest.fixture
def request_context():
    """Create a test RequestContext."""
    return RequestContext(
        request_id="test-001",
        model="qwen2.5-72b",
        quantization="awq",
        timeout=120.0,
    )


class TestQueueManagerCore:
    """Test Task 2.1: Core queue functionality."""

    @pytest.mark.asyncio
    async def test_get_or_create_queue_creates_new(self, queue_manager):
        """Test that get_or_create_queue creates a new queue."""
        queue = await queue_manager.get_or_create_queue("test-model")
        assert queue is not None
        assert "test-model" in queue_manager._queues

    @pytest.mark.asyncio
    async def test_get_or_create_queue_returns_existing(self, queue_manager):
        """Test that get_or_create_queue returns existing queue."""
        queue1 = await queue_manager.get_or_create_queue("test-model")
        queue2 = await queue_manager.get_or_create_queue("test-model")
        assert queue1 is queue2

    @pytest.mark.asyncio
    async def test_enqueue_creates_queue_on_first_request(self, queue_manager, request_context):
        """Test that enqueue creates queue if it doesn't exist."""
        model_quant = "qwen2.5-72b-awq"
        assert model_quant not in queue_manager._queues

        await queue_manager.enqueue(model_quant, request_context)

        assert model_quant in queue_manager._queues
        assert queue_manager._queues[model_quant].qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_dequeue_fifo_ordering(self, queue_manager):
        """Test that enqueue/dequeue maintains FIFO ordering."""
        model_quant = "test-model"

        # Enqueue 3 requests
        for i in range(3):
            ctx = RequestContext(
                request_id=f"req-{i}",
                model="test",
                quantization="awq",
            )
            await queue_manager.enqueue(model_quant, ctx)

        # Dequeue and verify FIFO order
        for i in range(3):
            ctx = await queue_manager.dequeue(model_quant)
            assert ctx.request_id == f"req-{i}"

    @pytest.mark.asyncio
    async def test_dequeue_raises_for_nonexistent_queue(self, queue_manager):
        """Test that dequeue raises KeyError for non-existent queue."""
        with pytest.raises(KeyError):
            await queue_manager.dequeue("nonexistent-model")

    @pytest.mark.asyncio
    async def test_destroy_queue_removes_queue(self, queue_manager, request_context):
        """Test that destroy_queue removes the queue."""
        model_quant = "test-model"
        await queue_manager.enqueue(model_quant, request_context)

        await queue_manager.destroy_queue(model_quant)

        assert model_quant not in queue_manager._queues
        assert model_quant not in queue_manager._active_counts
        assert model_quant not in queue_manager._last_used


class TestActiveTracking:
    """Test Task 2.2: Active tracking functionality."""

    @pytest.mark.asyncio
    async def test_increment_decrement_active(self, queue_manager):
        """Test increment/decrement active counts."""
        model_quant = "test-model"

        queue_manager.increment_active(model_quant)
        assert queue_manager._active_counts[model_quant] == 1

        queue_manager.increment_active(model_quant)
        assert queue_manager._active_counts[model_quant] == 2

        queue_manager.decrement_active(model_quant)
        assert queue_manager._active_counts[model_quant] == 1

        queue_manager.decrement_active(model_quant)
        assert queue_manager._active_counts[model_quant] == 0

    @pytest.mark.asyncio
    async def test_decrement_does_not_go_negative(self, queue_manager):
        """Test that decrement doesn't go below zero."""
        model_quant = "test-model"
        queue_manager._active_counts[model_quant] = 0

        queue_manager.decrement_active(model_quant)
        assert queue_manager._active_counts[model_quant] == 0

    @pytest.mark.asyncio
    async def test_is_idle(self, queue_manager):
        """Test is_idle functionality."""
        model_quant = "test-model"

        # Non-existent model is idle
        assert queue_manager.is_idle(model_quant)

        # Active model is not idle
        queue_manager.increment_active(model_quant)
        assert not queue_manager.is_idle(model_quant)

        # Back to idle
        queue_manager.decrement_active(model_quant)
        assert queue_manager.is_idle(model_quant)

    @pytest.mark.asyncio
    async def test_update_last_used(self, queue_manager):
        """Test last_used timestamp updates."""
        model_quant = "test-model"

        before = datetime.utcnow()
        queue_manager.update_last_used(model_quant)
        after = datetime.utcnow()

        assert model_quant in queue_manager._last_used
        assert before <= queue_manager._last_used[model_quant] <= after

    @pytest.mark.asyncio
    async def test_get_lru_idle_models(self, queue_manager):
        """Test LRU idle models sorting."""
        # Create 3 queues with different last_used times
        await queue_manager.get_or_create_queue("model-a")
        await queue_manager.get_or_create_queue("model-b")
        await queue_manager.get_or_create_queue("model-c")

        # Set different last_used times
        now = datetime.utcnow()
        queue_manager._last_used["model-a"] = now - timedelta(minutes=5)  # Oldest
        queue_manager._last_used["model-b"] = now - timedelta(minutes=2)
        queue_manager._last_used["model-c"] = now  # Newest

        # Make model-b active (not idle)
        queue_manager.increment_active("model-b")

        lru = queue_manager.get_lru_idle_models()

        # Should only include idle models, sorted by oldest first
        assert "model-b" not in lru  # Not idle
        assert lru[0] == "model-a"  # Oldest idle
        assert "model-c" in lru

    @pytest.mark.asyncio
    async def test_track_request_context_manager(self, queue_manager):
        """Test track_request context manager."""
        model_quant = "test-model"
        queue_manager._active_counts[model_quant] = 1  # Simulate enqueue increment

        async with queue_manager.track_request(model_quant):
            pass  # Simulate processing

        # Should have decremented and updated last_used
        assert queue_manager._active_counts[model_quant] == 0
        assert model_quant in queue_manager._last_used


class TestQueueMetrics:
    """Test Task 2.3: Metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_get_queue_status(self, queue_manager, request_context):
        """Test get_queue_status returns correct data."""
        model_quant = "test-model"
        await queue_manager.enqueue(model_quant, request_context)

        status = queue_manager.get_queue_status()

        assert model_quant in status
        assert status[model_quant]["depth"] == 1
        assert status[model_quant]["active_count"] == 1
        assert "last_used" in status[model_quant]

    @pytest.mark.asyncio
    async def test_get_queue_status_multiple_queues(self, queue_manager):
        """Test get_queue_status with multiple queues."""
        # Create multiple queues
        await queue_manager.get_or_create_queue("model-a")
        await queue_manager.get_or_create_queue("model-b")

        status = queue_manager.get_queue_status()

        assert len(status) == 2
        assert "model-a" in status
        assert "model-b" in status


class TestConcurrentAccess:
    """Test concurrent access to queue manager."""

    @pytest.mark.asyncio
    async def test_concurrent_enqueue(self, queue_manager):
        """Test concurrent enqueues don't cause issues."""
        model_quant = "test-model"

        async def enqueue_request(i):
            ctx = RequestContext(
                request_id=f"req-{i}",
                model="test",
                quantization="awq",
            )
            await queue_manager.enqueue(model_quant, ctx)

        # Enqueue 10 requests concurrently
        await asyncio.gather(*[enqueue_request(i) for i in range(10)])

        assert queue_manager._queues[model_quant].qsize() == 10
        assert queue_manager._active_counts[model_quant] == 10
