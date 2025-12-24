"""Queue manager for per-model FIFO request queues.

Manages asyncio queues for each model+quantization combination, tracks active
request counts, and provides LRU eviction data for idle models.
"""

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RequestContext:
    """Context for an inference request in the queue.

    This is a placeholder implementation. Will be expanded in Task 1.2
    with response events, stream queues, and error state.
    """
    request_id: str
    model: str
    quantization: Optional[str]
    enqueue_time: datetime = field(default_factory=datetime.utcnow)
    timeout: float = 120.0
    # Future fields from Task 1.2:
    # response_event: asyncio.Event
    # stream_queue: asyncio.Queue
    # error_state: Optional[Exception]


class QueueManager:
    """Manages per-model FIFO queues for inference requests.

    This service maintains separate asyncio queues for each model+quantization
    combination, tracks active request counts (in-queue + in-flight), and
    provides metrics for capacity planning and LRU eviction decisions.

    Thread-safe for concurrent access from multiple async tasks.
    """

    def __init__(self):
        """Initialize the queue manager."""
        # Dict of model+quant -> asyncio.Queue
        self._queues: Dict[str, asyncio.Queue] = {}

        # Lock for thread-safe queue creation
        self._lock: asyncio.Lock = asyncio.Lock()

        # Active request counts (in-queue + in-flight)
        self._active_counts: Dict[str, int] = {}

        # Last request completion timestamp
        self._last_used: Dict[str, datetime] = {}

        logger.info("queue_manager_initialized")

    async def get_or_create_queue(self, model_quant: str) -> asyncio.Queue:
        """Get or create a queue for model+quant.

        Args:
            model_quant: Model+quantization identifier (e.g., "qwen2.5-72b-awq")

        Returns:
            asyncio.Queue for this model+quant
        """
        async with self._lock:
            if model_quant not in self._queues:
                self._queues[model_quant] = asyncio.Queue()
                self._active_counts[model_quant] = 0
                self._last_used[model_quant] = datetime.utcnow()

                logger.info(
                    "queue_created",
                    model_quant=model_quant,
                    total_queues=len(self._queues),
                )

            return self._queues[model_quant]

    async def enqueue(
        self, model_quant: str, request_context: RequestContext
    ) -> None:
        """Add request to queue. Creates queue if needed.

        Args:
            model_quant: Model+quantization identifier
            request_context: Request context to enqueue
        """
        queue = await self.get_or_create_queue(model_quant)

        # Increment active count before enqueuing
        self.increment_active(model_quant)

        await queue.put(request_context)

        logger.info(
            "request_enqueued",
            request_id=request_context.request_id,
            model_quant=model_quant,
            queue_depth=queue.qsize(),
            active_count=self._active_counts.get(model_quant, 0),
        )

    async def dequeue(self, model_quant: str) -> RequestContext:
        """Get next request from queue. Blocks until available.

        Args:
            model_quant: Model+quantization identifier

        Returns:
            RequestContext for the next request

        Raises:
            KeyError: If queue does not exist
        """
        if model_quant not in self._queues:
            raise KeyError(f"Queue for {model_quant} does not exist")

        queue = self._queues[model_quant]
        enqueue_time = datetime.utcnow()

        # Block until request available
        request_context = await queue.get()

        # Calculate wait time
        wait_time = (datetime.utcnow() - request_context.enqueue_time).total_seconds()

        logger.info(
            "request_dequeued",
            request_id=request_context.request_id,
            model_quant=model_quant,
            wait_time_seconds=round(wait_time, 2),
            remaining_depth=queue.qsize(),
        )

        return request_context

    async def destroy_queue(self, model_quant: str) -> None:
        """Remove queue and reject any pending requests.

        Args:
            model_quant: Model+quantization identifier
        """
        async with self._lock:
            if model_quant not in self._queues:
                logger.warning(
                    "destroy_queue_not_found",
                    model_quant=model_quant,
                )
                return

            queue = self._queues[model_quant]
            pending_count = queue.qsize()

            # Drain queue (in future, set error state on RequestContext)
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            # Remove queue and metadata
            del self._queues[model_quant]
            if model_quant in self._active_counts:
                del self._active_counts[model_quant]
            if model_quant in self._last_used:
                del self._last_used[model_quant]

            logger.info(
                "queue_destroyed",
                model_quant=model_quant,
                pending_requests_rejected=pending_count,
            )

    def increment_active(self, model_quant: str) -> None:
        """Increment active count for model+quant.

        Args:
            model_quant: Model+quantization identifier
        """
        if model_quant not in self._active_counts:
            self._active_counts[model_quant] = 0

        self._active_counts[model_quant] += 1

        logger.debug(
            "active_count_incremented",
            model_quant=model_quant,
            active_count=self._active_counts[model_quant],
        )

    def decrement_active(self, model_quant: str) -> None:
        """Decrement active count for model+quant.

        Args:
            model_quant: Model+quantization identifier
        """
        if model_quant not in self._active_counts:
            logger.warning(
                "decrement_active_not_found",
                model_quant=model_quant,
            )
            return

        self._active_counts[model_quant] = max(
            0, self._active_counts[model_quant] - 1
        )

        logger.debug(
            "active_count_decremented",
            model_quant=model_quant,
            active_count=self._active_counts[model_quant],
        )

    def update_last_used(self, model_quant: str) -> None:
        """Update last_used timestamp to now.

        Args:
            model_quant: Model+quantization identifier
        """
        self._last_used[model_quant] = datetime.utcnow()

        logger.debug(
            "last_used_updated",
            model_quant=model_quant,
            timestamp=self._last_used[model_quant].isoformat(),
        )

    def is_idle(self, model_quant: str) -> bool:
        """Returns True if model has no active requests.

        Args:
            model_quant: Model+quantization identifier

        Returns:
            True if active_count == 0, False otherwise
        """
        return self._active_counts.get(model_quant, 0) == 0

    def get_lru_idle_models(self) -> List[str]:
        """Returns list of idle models sorted by last_used (oldest first).

        Returns:
            List of model+quant identifiers, sorted by LRU (oldest first)
        """
        # Filter to idle models
        idle_models = [
            model_quant
            for model_quant in self._queues.keys()
            if self.is_idle(model_quant)
        ]

        # Sort by last_used timestamp (oldest first)
        idle_models.sort(key=lambda m: self._last_used.get(m, datetime.min))

        logger.debug(
            "lru_idle_models_retrieved",
            count=len(idle_models),
            models=idle_models[:5] if idle_models else [],  # Log first 5
        )

        return idle_models

    @contextlib.asynccontextmanager
    async def track_request(
        self, model_quant: str
    ) -> AsyncIterator[None]:
        """Context manager to auto track active count.

        This context manager automatically increments the active count on entry
        and decrements it on exit, while also updating the last_used timestamp.

        Note: For enqueued requests, increment_active is called in enqueue(),
        so this context manager should be used for the processing phase only.

        Args:
            model_quant: Model+quantization identifier

        Yields:
            None

        Example:
            async with queue_manager.track_request(model_quant):
                # Process request
                result = await forward_to_container(request)
                # Active count auto-decremented and last_used updated on exit
        """
        # Note: Don't increment here if already incremented in enqueue()
        # This context manager is for tracking the processing phase
        try:
            yield
        finally:
            self.decrement_active(model_quant)
            self.update_last_used(model_quant)

    def get_queue_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all queues.

        Returns:
            Dict mapping model+quant to:
                - depth: Number of requests in queue
                - active_count: Number of active requests (in-queue + in-flight)
                - last_used: ISO timestamp of last completed request
        """
        status = {}

        for model_quant, queue in self._queues.items():
            status[model_quant] = {
                "depth": queue.qsize(),
                "active_count": self._active_counts.get(model_quant, 0),
                "last_used": (
                    self._last_used.get(model_quant, datetime.min).isoformat()
                ),
            }

        return status


# Singleton instance
queue_manager = QueueManager()
