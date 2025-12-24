# Phase 5 Implementation: Tasks 6.1, 6.2, and 6.3

**Status**: ✅ Complete
**Date**: 2025-12-24

## Overview

Successfully implemented timeout scaling, configuration loading, and timeout enforcement infrastructure for the LLM Serve Dashboard Phase 5 request routing system.

## Task 6.1: Timeout Scaling by Model Size

**File**: `/data/home/mgreger/proj/llms/dashboard/backend/services/timeout_calculator.py`

### Features Implemented

1. **Model Size Tier Classification**
   - `ModelSizeTier` enum with 5 tiers: TINY, SMALL, MEDIUM, LARGE, XLARGE
   - `get_model_size_tier()` function to classify models by parameter count
   - Thresholds: <3B, 3-10B, 10-30B, 30-70B, 70B+

2. **Loading Timeout Calculation**
   - `calculate_loading_timeout()` with tier-based timeouts
   - Base timeouts: 60s (TINY) to 240s (XLARGE)
   - Multi-machine deployment support (+120s extra)
   - Comprehensive logging for monitoring

3. **Inference Timeout Calculation**
   - `calculate_inference_timeout()` for request-specific timeouts
   - Adjusts for model size (larger models generate slower)
   - Speed multipliers: 1.0 (TINY/SMALL) to 0.4 (XLARGE)
   - Formula: `base_timeout + (max_tokens / adjusted_tps) * 1.1`
   - 10% buffer for variance

4. **Parameter Extraction**
   - `extract_param_count_from_name()` for parsing model names
   - Supports common patterns: "mistral-7b", "qwen2.5-72b-instruct", "llama3.1-8b-chat"
   - Special handling for phi-3, gemma-2, etc.
   - Returns None for unknown patterns

5. **Timeout Enforcement Helper**
   - `with_timeout()` async wrapper for coroutines
   - Automatic logging of operation start/completion/timeout
   - Context passing for rich log data
   - Proper error handling and re-raising

### Example Usage

```python
from services.timeout_calculator import (
    calculate_loading_timeout,
    calculate_inference_timeout,
    extract_param_count_from_name,
    with_timeout
)

# Extract model size
params = extract_param_count_from_name("llama3.1-70b-chat")  # 70.0

# Calculate loading timeout
loading_timeout = calculate_loading_timeout(
    params_billions=params,
    multi_machine=True  # 180 + 120 = 300 seconds
)

# Calculate inference timeout
inference_timeout = calculate_inference_timeout(
    max_tokens=1000,
    params_billions=params,
    tokens_per_second=25.0
)

# Use timeout wrapper
result = await with_timeout(
    load_model("llama3.1-70b-chat"),
    timeout_seconds=loading_timeout,
    operation="model_loading",
    context={"model": "llama3.1-70b-chat"}
)
```

## Task 6.2: Configuration Loading

**File**: `/data/home/mgreger/proj/llms/dashboard/backend/config.py`

### Features Implemented

1. **RouterConfig Class**
   - Extends Pydantic v2 `BaseSettings`
   - Environment variable prefix: `ROUTER_`
   - Automatic .env file loading
   - Validation with min/max constraints

2. **Configuration Parameters**

   | Parameter | Default | Range | Description |
   |-----------|---------|-------|-------------|
   | `default_loading_timeout` | 120 | 30-600 | Default model loading timeout (seconds) |
   | `default_inference_timeout` | 120 | 30-3600 | Default inference timeout (seconds) |
   | `keepalive_interval` | 1.0 | 0.1-10.0 | SSE keepalive interval (seconds) |
   | `max_gpus_per_machine` | 8 | 1-16 | Max GPUs for multi-machine detection |
   | `max_queue_size` | 100 | 1-1000 | Max requests per model queue |

3. **Singleton Pattern**
   - `get_router_config()` function with `@lru_cache`
   - Ensures configuration loaded only once
   - Same pattern as existing `get_settings()`

4. **Environment Variable Support**

   ```bash
   # .env file or environment
   ROUTER_DEFAULT_LOADING_TIMEOUT=180
   ROUTER_DEFAULT_INFERENCE_TIMEOUT=300
   ROUTER_KEEPALIVE_INTERVAL=2.0
   ROUTER_MAX_GPUS_PER_MACHINE=8
   ROUTER_MAX_QUEUE_SIZE=200
   ```

### Example Usage

```python
from config import get_router_config, router_config

# Get configuration (singleton)
config = get_router_config()

# Or use pre-initialized instance
print(config.default_loading_timeout)  # 120
print(config.max_queue_size)  # 100

# Use in router
if request_queue.qsize() >= config.max_queue_size:
    raise QueueFullError("Model queue at capacity")
```

## Task 6.3: Timeout Enforcement

**Implementation**: Integrated into `timeout_calculator.py` via `with_timeout()` helper

### Features

1. **Async Timeout Wrapper**
   - Wraps any coroutine with timeout enforcement
   - Uses `asyncio.wait_for()` under the hood
   - Automatic structured logging

2. **Logging Integration**
   - Logs operation start with context
   - Logs successful completion
   - Logs timeout errors with full context
   - Logs other exceptions with error details

3. **Error Handling**
   - Raises `asyncio.TimeoutError` on timeout
   - Re-raises original exceptions
   - Preserves stack traces

### Example Usage

```python
from services.timeout_calculator import with_timeout

# Model loading with timeout
model = await with_timeout(
    daemon_client.load_model(model_id),
    timeout_seconds=calculate_loading_timeout(params, multi_machine=True),
    operation="model_loading",
    context={
        "model_id": model_id,
        "params_billions": params,
        "multi_machine": True
    }
)

# Inference with timeout
response = await with_timeout(
    daemon_client.generate(prompt, max_tokens=500),
    timeout_seconds=calculate_inference_timeout(500, params),
    operation="inference",
    context={
        "model_id": model_id,
        "max_tokens": 500
    }
)
```

## Integration Points

### Service Layer Export

Updated `/data/home/mgreger/proj/llms/dashboard/backend/services/__init__.py`:

```python
from .timeout_calculator import (
    ModelSizeTier,
    get_model_size_tier,
    calculate_loading_timeout,
    calculate_inference_timeout,
    extract_param_count_from_name,
    with_timeout,
)
```

All timeout calculator functions are now available via:
```python
from services import calculate_loading_timeout, with_timeout
```

### Configuration Export

Updated `/data/home/mgreger/proj/llms/dashboard/backend/config.py`:

```python
router_config = get_router_config()
```

Router configuration available via:
```python
from config import router_config
```

## Testing

**Test File**: `/data/home/mgreger/proj/llms/test_timeout_implementation.py`

Comprehensive test suite covering:
- ✅ Model size tier classification
- ✅ Loading timeout calculation (single and multi-machine)
- ✅ Inference timeout calculation
- ✅ Parameter extraction from model names
- ✅ Timeout enforcement with async wrapper
- ✅ Router configuration loading and singleton pattern

Run tests with:
```bash
python3 test_timeout_implementation.py
```

## Design Decisions

1. **Tiered Timeout Approach**
   - Simplifies configuration vs. per-model settings
   - Provides reasonable defaults for common model sizes
   - Easy to understand and debug

2. **Multi-Machine Detection**
   - Added 120s extra for distributed loading coordination
   - Accounts for network latency and synchronization overhead
   - Configurable via `max_gpus_per_machine` threshold

3. **Inference Speed Adjustment**
   - Larger models generate slower (40-100% of base speed)
   - Based on empirical observations of LLM performance
   - Conservative estimates to reduce timeout failures

4. **Structured Logging**
   - Uses `structlog` for consistent, parseable logs
   - Includes rich context for debugging
   - Enables monitoring and alerting integration

5. **Validation and Type Safety**
   - Pydantic validation on all config parameters
   - Type hints throughout for IDE support
   - Range constraints prevent invalid configurations

## Future Enhancements

1. **Dynamic Timeout Adjustment**
   - Learn from actual inference times
   - Adjust timeouts based on observed performance
   - Per-model timeout overrides

2. **Advanced Model Name Parsing**
   - Support for more model naming conventions
   - Integration with model metadata database
   - Fallback to API calls for unknown models

3. **Circuit Breaker Pattern**
   - Track timeout rates per model
   - Temporarily disable models with high failure rates
   - Automatic recovery with backoff

4. **Metrics Integration**
   - Export timeout events to TimescaleDB
   - Dashboard for timeout analysis
   - Alerts for abnormal timeout rates

## Files Modified/Created

### Created
1. `/data/home/mgreger/proj/llms/dashboard/backend/services/timeout_calculator.py` (273 lines)
2. `/data/home/mgreger/proj/llms/test_timeout_implementation.py` (156 lines)
3. `/data/home/mgreger/proj/llms/PHASE5_TASKS_6.1-6.3_IMPLEMENTATION.md` (this file)

### Modified
1. `/data/home/mgreger/proj/llms/dashboard/backend/config.py`
   - Added `RouterConfig` class
   - Added `get_router_config()` function
   - Added `router_config` singleton export

2. `/data/home/mgreger/proj/llms/dashboard/backend/services/__init__.py`
   - Added timeout_calculator exports
   - Updated `__all__` list

## Dependencies

All dependencies already present in the project:
- `pydantic` and `pydantic-settings` (for configuration)
- `structlog` (for logging)
- `asyncio` (standard library)

No new dependencies required.

## Next Steps

The timeout infrastructure is now ready for integration into:
- **Task 6.4**: Queue Management (use `max_queue_size` config)
- **Task 6.5**: Model Router (use all timeout functions)
- **Task 6.6**: SSE Streaming (use `keepalive_interval` config)

All timeout calculation, configuration, and enforcement utilities are available through the service layer for immediate use.
