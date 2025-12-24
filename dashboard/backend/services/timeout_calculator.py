"""Timeout calculation based on model size and operation type."""

import asyncio
import re
from enum import Enum
from typing import Awaitable, Optional, TypeVar
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class ModelSizeTier(Enum):
    """Model size tiers for timeout calculation."""
    TINY = "tiny"      # < 3B
    SMALL = "small"    # 3-10B
    MEDIUM = "medium"  # 10-30B
    LARGE = "large"    # 30-70B
    XLARGE = "xlarge"  # 70B+


# Loading timeout tiers in seconds
LOADING_TIMEOUTS = {
    ModelSizeTier.TINY: 60,
    ModelSizeTier.SMALL: 90,
    ModelSizeTier.MEDIUM: 120,
    ModelSizeTier.LARGE: 180,
    ModelSizeTier.XLARGE: 240,
}

# Add extra time for multi-machine deployments
MULTI_MACHINE_EXTRA_SECONDS = 120


def get_model_size_tier(params_billions: float) -> ModelSizeTier:
    """Get size tier from parameter count in billions.

    Args:
        params_billions: Model parameter count in billions

    Returns:
        ModelSizeTier corresponding to the parameter count

    Examples:
        >>> get_model_size_tier(1.5)
        ModelSizeTier.TINY
        >>> get_model_size_tier(7.0)
        ModelSizeTier.SMALL
        >>> get_model_size_tier(72.0)
        ModelSizeTier.XLARGE
    """
    if params_billions < 3:
        return ModelSizeTier.TINY
    elif params_billions < 10:
        return ModelSizeTier.SMALL
    elif params_billions < 30:
        return ModelSizeTier.MEDIUM
    elif params_billions < 70:
        return ModelSizeTier.LARGE
    else:
        return ModelSizeTier.XLARGE


def calculate_loading_timeout(
    params_billions: float,
    multi_machine: bool = False
) -> int:
    """Calculate timeout for model loading in seconds.

    Args:
        params_billions: Model parameter count in billions
        multi_machine: Whether this is a multi-machine deployment

    Returns:
        Timeout in seconds

    Examples:
        >>> calculate_loading_timeout(7.0)
        90
        >>> calculate_loading_timeout(7.0, multi_machine=True)
        210
        >>> calculate_loading_timeout(72.0)
        240
    """
    tier = get_model_size_tier(params_billions)
    base_timeout = LOADING_TIMEOUTS[tier]

    if multi_machine:
        timeout = base_timeout + MULTI_MACHINE_EXTRA_SECONDS
        logger.info(
            "calculated_loading_timeout",
            params_billions=params_billions,
            tier=tier.value,
            multi_machine=multi_machine,
            base_timeout=base_timeout,
            final_timeout=timeout
        )
        return timeout

    logger.debug(
        "calculated_loading_timeout",
        params_billions=params_billions,
        tier=tier.value,
        timeout=base_timeout
    )
    return base_timeout


def calculate_inference_timeout(
    max_tokens: int,
    params_billions: float = 7.0,
    tokens_per_second: float = 30.0,
    base_timeout: float = 30.0
) -> float:
    """Calculate timeout for inference request.

    Args:
        max_tokens: Maximum tokens to generate
        params_billions: Model size (affects generation speed)
        tokens_per_second: Estimated tokens/sec (varies by model)
        base_timeout: Base timeout for request processing

    Returns:
        Timeout in seconds

    Examples:
        >>> calculate_inference_timeout(100)
        33.33...
        >>> calculate_inference_timeout(1000, tokens_per_second=50.0)
        50.0
        >>> calculate_inference_timeout(500, params_billions=72.0, tokens_per_second=15.0)
        63.33...
    """
    # Adjust tokens per second based on model size
    # Larger models generate slower
    tier = get_model_size_tier(params_billions)

    # Apply speed penalty for larger models
    speed_multipliers = {
        ModelSizeTier.TINY: 1.0,
        ModelSizeTier.SMALL: 1.0,
        ModelSizeTier.MEDIUM: 0.8,
        ModelSizeTier.LARGE: 0.6,
        ModelSizeTier.XLARGE: 0.4,
    }

    adjusted_tps = tokens_per_second * speed_multipliers[tier]

    # Calculate time to generate tokens
    generation_time = max_tokens / adjusted_tps

    # Total timeout = base processing + generation time + 10% buffer
    timeout = base_timeout + generation_time * 1.1

    logger.debug(
        "calculated_inference_timeout",
        max_tokens=max_tokens,
        params_billions=params_billions,
        tier=tier.value,
        base_tps=tokens_per_second,
        adjusted_tps=adjusted_tps,
        generation_time=generation_time,
        timeout=timeout
    )

    return timeout


def extract_param_count_from_name(model_name: str) -> Optional[float]:
    """Extract parameter count from model name.

    Examples:
        >>> extract_param_count_from_name("qwen2.5-72b-instruct")
        72.0
        >>> extract_param_count_from_name("llama3.1-8b-chat")
        8.0
        >>> extract_param_count_from_name("mistral-7b")
        7.0
        >>> extract_param_count_from_name("unknown-model")
        None
        >>> extract_param_count_from_name("phi-3-mini-4k-instruct")
        3.0
        >>> extract_param_count_from_name("gemma-2-27b")
        27.0
    """
    # Common patterns for parameter counts in model names
    # Handles: 7b, 72b, 8B, 1.5b, 3b, etc.
    patterns = [
        r'[-_](\d+\.?\d*)[bB][-_]',  # -7b-, -72b-, -8B-
        r'[-_](\d+\.?\d*)[bB]$',     # -7b, -72B at end
        r'^(\d+\.?\d*)[bB][-_]',     # 7b-, 8B- at start
        r'[-_]phi[-_](\d+)',          # phi-3
        r'[-_]gemma[-_](\d+)',        # gemma-2
    ]

    for pattern in patterns:
        match = re.search(pattern, model_name, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                logger.debug(
                    "extracted_param_count",
                    model_name=model_name,
                    pattern=pattern,
                    value=value
                )
                return value
            except (ValueError, IndexError):
                continue

    logger.debug(
        "no_param_count_extracted",
        model_name=model_name
    )
    return None


async def with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float,
    operation: str = "operation",
    context: Optional[dict] = None
) -> T:
    """Execute coroutine with timeout and logging.

    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds
        operation: Operation name for logging
        context: Additional context for logging

    Returns:
        Result of coroutine

    Raises:
        asyncio.TimeoutError: If operation times out

    Examples:
        >>> import asyncio
        >>> async def quick_task():
        ...     await asyncio.sleep(0.1)
        ...     return "done"
        >>> asyncio.run(with_timeout(quick_task(), 1.0, "test"))
        'done'
    """
    log_context = {
        "operation": operation,
        "timeout_seconds": timeout_seconds,
    }
    if context:
        log_context.update(context)

    logger.debug("operation_started", **log_context)

    try:
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        logger.debug("operation_completed", **log_context)
        return result
    except asyncio.TimeoutError:
        logger.error(
            "operation_timed_out",
            **log_context
        )
        raise
    except Exception as e:
        logger.error(
            "operation_failed",
            error=str(e),
            error_type=type(e).__name__,
            **log_context
        )
        raise
