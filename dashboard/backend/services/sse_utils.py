"""SSE streaming utilities for the request router.

Provides utilities for Server-Sent Events (SSE) streaming, including:
- SSE response formatting
- Keepalive message generation during model loading
- Seamless transition from keepalive to response streaming
"""

import asyncio
import json
import time
from typing import AsyncIterator, Union

import structlog

logger = structlog.get_logger(__name__)


def format_sse_data(data: Union[dict, str]) -> str:
    """Format data as SSE data line.

    Args:
        data: Dictionary to encode as JSON, or string to send as-is

    Returns:
        SSE-formatted data line: "data: {content}\n\n"
    """
    if isinstance(data, dict):
        content = json.dumps(data)
    else:
        content = str(data)

    return f"data: {content}\n\n"


def format_sse_comment(comment: str) -> str:
    """Format as SSE comment (starts with :).

    Args:
        comment: Comment text

    Returns:
        SSE-formatted comment: ": {comment}\n\n"
    """
    return f": {comment}\n\n"


def create_error_chunk(error_message: str, error_type: str = "server_error") -> str:
    """Create an SSE-formatted error chunk in OpenAI format.

    Args:
        error_message: Human-readable error message
        error_type: Error type identifier (default: "server_error")

    Returns:
        SSE-formatted error chunk
    """
    error_data = {
        "error": {
            "message": error_message,
            "type": error_type,
            "code": None,
        }
    }
    return format_sse_data(error_data)


async def sse_generator(
    async_iterator: AsyncIterator[Union[dict, str]],
    include_done: bool = True
) -> AsyncIterator[str]:
    """Wrap an async iterator to yield SSE-formatted chunks.

    This generator wraps an async iterator and formats its output as
    Server-Sent Events (SSE). It handles:
    - Dict items: Converted to JSON and yielded as "data: {json}\n\n"
    - String items starting with ":": Passed through as SSE comments
    - Other string items: Yielded as "data: {str}\n\n"
    - End of stream: Yields "data: [DONE]\n\n" if include_done=True
    - Errors: Yields error chunk and closes stream

    Args:
        async_iterator: Async iterator yielding dicts or strings
        include_done: Whether to send [DONE] message at end (default: True)

    Yields:
        SSE-formatted strings

    Example:
        async def data_source():
            yield {"content": "hello"}
            yield {"content": "world"}

        async for chunk in sse_generator(data_source()):
            print(chunk)  # "data: {...}\n\n"
    """
    try:
        async for item in async_iterator:
            if isinstance(item, str) and item.startswith(":"):
                # Pass through SSE comments as-is
                yield item if item.endswith("\n\n") else f"{item}\n\n"
            elif isinstance(item, dict):
                # Format dict as JSON data
                yield format_sse_data(item)
            else:
                # Format string as data
                yield format_sse_data(str(item))

    except Exception as e:
        # Send error chunk on exception
        logger.error(
            "sse_generator_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        yield create_error_chunk(
            error_message=f"Stream error: {str(e)}",
            error_type=type(e).__name__,
        )
        return

    # Send [DONE] marker at end of successful stream
    if include_done:
        yield format_sse_data("[DONE]")


async def keepalive_generator(
    loading_event: asyncio.Event,
    model_name: str,
    estimated_seconds: int = 60,
    interval: float = 1.0
) -> AsyncIterator[str]:
    """Generate keepalive SSE comments while waiting for model to load.

    This generator yields SSE comment messages at regular intervals while
    waiting for a model to finish loading. It shows a countdown of estimated
    time remaining and stops when the loading event is set or time runs out.

    Args:
        loading_event: Event that will be set when loading completes
        model_name: Name of the model being loaded
        estimated_seconds: Estimated total loading time in seconds
        interval: Time between keepalive messages in seconds (default: 1.0)

    Yields:
        SSE comment strings like ": loading qwen2.5-72b-instruct, ~45s remaining\n\n"

    Example:
        loading_event = asyncio.Event()
        async for msg in keepalive_generator(loading_event, "llama3-8b", 120):
            print(msg)  # ": loading llama3-8b, ~119s remaining\n\n"
    """
    start_time = time.time()

    while not loading_event.is_set():
        elapsed = time.time() - start_time
        remaining = max(0, estimated_seconds - int(elapsed))

        # Generate keepalive comment with countdown
        comment = f"loading {model_name}, ~{remaining}s remaining"
        yield format_sse_comment(comment)

        logger.debug(
            "keepalive_sent",
            model_name=model_name,
            elapsed=int(elapsed),
            remaining=remaining,
        )

        # Check if we've exceeded the estimated time
        if remaining <= 0:
            logger.warning(
                "keepalive_timeout_exceeded",
                model_name=model_name,
                estimated_seconds=estimated_seconds,
                elapsed=int(elapsed),
            )
            break

        # Wait for interval or until loading completes
        try:
            await asyncio.wait_for(
                loading_event.wait(),
                timeout=interval
            )
            # Event was set, break out of loop
            break
        except asyncio.TimeoutError:
            # Interval elapsed, continue loop
            continue


async def stream_with_keepalive(
    loading_task: asyncio.Task,
    loading_event: asyncio.Event,
    response_generator: AsyncIterator[str],
    model_name: str,
    estimated_load_seconds: int = 60
) -> AsyncIterator[str]:
    """Stream keepalive messages during loading, then transition to response.

    This function provides a seamless SSE stream that:
    1. Yields keepalive messages while the loading task is running
    2. Transitions to yielding from the response generator once loading completes
    3. Handles errors in either phase gracefully

    The client receives an uninterrupted SSE stream from request submission
    through model loading and into actual response streaming.

    Args:
        loading_task: Async task that completes when loading finishes
        loading_event: Event that will be set when loading completes
        response_generator: Async iterator that yields response chunks
        model_name: Name of the model being loaded
        estimated_load_seconds: Estimated loading time for countdown

    Yields:
        SSE-formatted strings (keepalive comments, then response data)

    Raises:
        Exception: If loading task fails or response streaming fails

    Example:
        loading_event = asyncio.Event()
        loading_task = asyncio.create_task(load_model())

        async def responses():
            yield {"content": "Hello"}

        async for chunk in stream_with_keepalive(
            loading_task, loading_event, responses(), "llama3-8b"
        ):
            print(chunk)  # Keepalive comments, then response chunks
    """
    try:
        # Phase 1: Stream keepalive messages during loading
        if not loading_event.is_set():
            logger.info(
                "streaming_keepalive_phase",
                model_name=model_name,
                estimated_seconds=estimated_load_seconds,
            )

            async for keepalive_msg in keepalive_generator(
                loading_event,
                model_name,
                estimated_load_seconds,
            ):
                yield keepalive_msg

                # Check if loading completed or failed
                if loading_task.done():
                    # Check for errors in loading task
                    try:
                        loading_task.result()
                    except Exception as e:
                        logger.error(
                            "loading_task_failed",
                            model_name=model_name,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        yield create_error_chunk(
                            error_message=f"Model loading failed: {str(e)}",
                            error_type="model_load_error",
                        )
                        return
                    break

        # Ensure loading actually completed
        if not loading_event.is_set():
            logger.warning(
                "loading_timeout",
                model_name=model_name,
                estimated_seconds=estimated_load_seconds,
            )
            yield create_error_chunk(
                error_message=f"Model loading timeout after {estimated_load_seconds}s",
                error_type="timeout_error",
            )
            return

        logger.info(
            "streaming_response_phase",
            model_name=model_name,
        )

        # Phase 2: Stream actual response from container
        async for response_chunk in response_generator:
            yield response_chunk

    except asyncio.CancelledError:
        logger.info(
            "stream_cancelled",
            model_name=model_name,
        )
        # Don't yield error on cancellation, just stop
        raise

    except Exception as e:
        logger.error(
            "stream_error",
            model_name=model_name,
            error=str(e),
            error_type=type(e).__name__,
        )
        yield create_error_chunk(
            error_message=f"Streaming error: {str(e)}",
            error_type=type(e).__name__,
        )
