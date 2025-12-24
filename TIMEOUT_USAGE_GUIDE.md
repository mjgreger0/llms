# Timeout Infrastructure Usage Guide

**Phase 5 Tasks 6.1-6.3 Implementation**

This guide shows how to use the timeout calculation and enforcement infrastructure in the model router and other Phase 5 components.

## Quick Start

```python
from config import router_config
from services import (
    calculate_loading_timeout,
    calculate_inference_timeout,
    extract_param_count_from_name,
    with_timeout
)
```

## Common Use Cases

### 1. Model Loading with Timeout

```python
async def load_model_safely(
    model_name: str,
    gpu_count: int,
    daemon_client: DaemonClient
) -> ModelInstance:
    """Load a model with appropriate timeout."""

    # Extract model size from name
    params = extract_param_count_from_name(model_name)
    if params is None:
        # Fallback to default (7B)
        params = 7.0
        logger.warning(
            "unknown_model_size",
            model_name=model_name,
            using_default=params
        )

    # Determine if multi-machine
    multi_machine = gpu_count > router_config.max_gpus_per_machine

    # Calculate timeout
    timeout = calculate_loading_timeout(
        params_billions=params,
        multi_machine=multi_machine
    )

    # Load with timeout enforcement
    try:
        model = await with_timeout(
            daemon_client.load_model(model_name, gpu_count),
            timeout_seconds=timeout,
            operation="model_loading",
            context={
                "model_name": model_name,
                "params_billions": params,
                "gpu_count": gpu_count,
                "multi_machine": multi_machine
            }
        )
        return model
    except asyncio.TimeoutError:
        logger.error(
            "model_loading_timeout",
            model_name=model_name,
            timeout=timeout,
            params=params
        )
        raise
```

### 2. Inference Request with Timeout

```python
async def generate_with_timeout(
    prompt: str,
    max_tokens: int,
    model_info: dict,
    daemon_client: DaemonClient
) -> str:
    """Run inference with appropriate timeout."""

    # Get model parameters
    params = model_info.get("params_billions", 7.0)

    # Calculate timeout based on expected generation time
    timeout = calculate_inference_timeout(
        max_tokens=max_tokens,
        params_billions=params,
        tokens_per_second=model_info.get("tokens_per_second", 30.0)
    )

    # Generate with timeout
    try:
        response = await with_timeout(
            daemon_client.generate(prompt, max_tokens=max_tokens),
            timeout_seconds=timeout,
            operation="inference",
            context={
                "model_name": model_info["name"],
                "max_tokens": max_tokens,
                "params_billions": params
            }
        )
        return response
    except asyncio.TimeoutError:
        logger.error(
            "inference_timeout",
            model=model_info["name"],
            max_tokens=max_tokens,
            timeout=timeout
        )
        raise
```

### 3. Queue Management with Config

```python
class ModelQueue:
    """Request queue for a specific model."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.queue = asyncio.Queue(maxsize=router_config.max_queue_size)

    async def enqueue(self, request: InferenceRequest) -> None:
        """Add request to queue."""
        if self.queue.qsize() >= router_config.max_queue_size:
            raise QueueFullError(
                f"Queue for {self.model_name} is full "
                f"({router_config.max_queue_size} requests)"
            )

        await self.queue.put(request)

    async def dequeue(self) -> InferenceRequest:
        """Get next request from queue."""
        return await self.queue.get()
```

### 4. SSE Streaming with Keepalive

```python
async def stream_response(
    request: InferenceRequest,
    daemon_client: DaemonClient
) -> AsyncIterator[str]:
    """Stream inference response with keepalive."""

    last_data_time = time.time()

    async for chunk in daemon_client.generate_stream(request.prompt):
        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        last_data_time = time.time()

        # Send keepalive if no data for keepalive_interval
        if time.time() - last_data_time > router_config.keepalive_interval:
            yield ": keepalive\n\n"
            last_data_time = time.time()
```

### 5. Smart Timeout Calculation

```python
def get_request_timeout(request: InferenceRequest) -> float:
    """Calculate timeout for a specific request."""

    # Extract model parameters
    params = extract_param_count_from_name(request.model_name)
    if params is None:
        # Use default timeout from config
        return router_config.default_inference_timeout

    # Use calculated timeout
    return calculate_inference_timeout(
        max_tokens=request.max_tokens or 512,
        params_billions=params,
        tokens_per_second=request.tokens_per_second or 30.0
    )
```

## Model Router Integration Example

```python
class ModelRouter:
    """Routes inference requests to appropriate model instances."""

    def __init__(self):
        self.config = router_config
        self.queues: dict[str, ModelQueue] = {}
        self.models: dict[str, ModelInstance] = {}

    async def load_model(
        self,
        model_name: str,
        gpu_count: int,
        daemon_client: DaemonClient
    ) -> None:
        """Load model with timeout."""

        # Extract parameters
        params = extract_param_count_from_name(model_name) or 7.0
        multi_machine = gpu_count > self.config.max_gpus_per_machine

        # Calculate timeout
        timeout = calculate_loading_timeout(params, multi_machine)

        # Load model
        model = await with_timeout(
            daemon_client.load_model(model_name, gpu_count),
            timeout_seconds=timeout,
            operation="model_loading",
            context={
                "model_name": model_name,
                "params": params,
                "gpus": gpu_count
            }
        )

        self.models[model_name] = model

    async def route_request(
        self,
        request: InferenceRequest
    ) -> InferenceResponse:
        """Route request to model with timeout."""

        # Get or create queue
        if request.model_name not in self.queues:
            self.queues[request.model_name] = ModelQueue(request.model_name)

        queue = self.queues[request.model_name]

        # Enqueue with timeout
        try:
            await with_timeout(
                queue.enqueue(request),
                timeout_seconds=5.0,  # Queue timeout
                operation="enqueue",
                context={"model": request.model_name}
            )
        except asyncio.TimeoutError:
            raise QueueTimeoutError("Failed to enqueue request")

        # Process request
        model = self.models[request.model_name]
        timeout = get_request_timeout(request)

        return await with_timeout(
            model.generate(request.prompt, request.max_tokens),
            timeout_seconds=timeout,
            operation="inference",
            context={
                "model": request.model_name,
                "max_tokens": request.max_tokens
            }
        )
```

## Configuration Examples

### Development Environment (.env)

```bash
# Shorter timeouts for testing
ROUTER_DEFAULT_LOADING_TIMEOUT=60
ROUTER_DEFAULT_INFERENCE_TIMEOUT=30
ROUTER_KEEPALIVE_INTERVAL=0.5
ROUTER_MAX_GPUS_PER_MACHINE=4
ROUTER_MAX_QUEUE_SIZE=50
```

### Production Environment (.env)

```bash
# Production timeouts
ROUTER_DEFAULT_LOADING_TIMEOUT=180
ROUTER_DEFAULT_INFERENCE_TIMEOUT=300
ROUTER_KEEPALIVE_INTERVAL=2.0
ROUTER_MAX_GPUS_PER_MACHINE=8
ROUTER_MAX_QUEUE_SIZE=200
```

## Best Practices

### 1. Always Provide Context

```python
# Good
await with_timeout(
    operation(),
    timeout_seconds=30,
    operation="model_loading",
    context={
        "model": model_name,
        "params": params,
        "machine": machine_id
    }
)

# Bad - no context for debugging
await with_timeout(operation(), 30)
```

### 2. Handle Timeouts Gracefully

```python
try:
    result = await with_timeout(operation(), timeout)
except asyncio.TimeoutError:
    # Log the failure
    logger.error("operation_timeout", operation="model_loading")

    # Clean up resources
    await cleanup()

    # Return appropriate error to user
    raise HTTPException(
        status_code=504,
        detail="Model loading timed out"
    )
```

### 3. Use Appropriate Fallbacks

```python
# Try to extract parameters
params = extract_param_count_from_name(model_name)

if params is None:
    # Check database
    params = await db.get_model_params(model_name)

if params is None:
    # Use conservative default
    params = 70.0  # Assume large model
    logger.warning("unknown_model_size", model=model_name)
```

### 4. Monitor Timeout Rates

```python
async def with_timeout_and_metrics(
    coro: Awaitable[T],
    timeout_seconds: float,
    operation: str,
    context: dict
) -> T:
    """Wrapper that also tracks timeout metrics."""

    start_time = time.time()
    try:
        result = await with_timeout(coro, timeout_seconds, operation, context)

        # Track success
        await metrics.record_operation_success(
            operation=operation,
            duration=time.time() - start_time
        )

        return result
    except asyncio.TimeoutError:
        # Track timeout
        await metrics.record_operation_timeout(
            operation=operation,
            timeout=timeout_seconds
        )
        raise
```

## Debugging Tips

### Enable Debug Logging

```python
import structlog

# Configure structlog for detailed output
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Check Timeout Calculation

```python
# Print timeout calculation details
params = extract_param_count_from_name("llama3.1-70b")
print(f"Parameters: {params}B")

timeout = calculate_loading_timeout(params, multi_machine=True)
print(f"Loading timeout: {timeout}s")

timeout = calculate_inference_timeout(1000, params)
print(f"Inference timeout (1000 tokens): {timeout}s")
```

### Test Timeout Behavior

```python
# Simulate slow operation
async def slow_operation():
    await asyncio.sleep(10)
    return "done"

# Should timeout after 2 seconds
try:
    result = await with_timeout(
        slow_operation(),
        timeout_seconds=2.0,
        operation="test"
    )
except asyncio.TimeoutError:
    print("Operation timed out as expected")
```

## Summary

The timeout infrastructure provides:

1. **Smart Timeout Calculation** - Based on model size and operation type
2. **Configuration Management** - Environment-based settings with validation
3. **Timeout Enforcement** - Async wrapper with automatic logging
4. **Multi-Machine Support** - Extra time for distributed deployments
5. **Type Safety** - Full type hints and Pydantic validation

All components are ready for integration into the model router (Tasks 6.4-6.6).
