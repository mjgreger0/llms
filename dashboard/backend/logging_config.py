"""
Structured logging configuration for LLM Serve Dashboard backend.

This module configures structlog for JSON-based structured logging with:
- Timestamp in ISO format
- Log level filtering based on environment variables
- Request ID propagation via contextvars
- Stack info for errors
- Configurable output format (JSON for production, console for development)
"""

import logging
import os
import sys
from contextvars import ContextVar
from typing import Any, Dict

import structlog
from structlog.types import EventDict, Processor


# ContextVar for request ID propagation
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add request ID from context to log entries.

    Args:
        logger: The logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary to be logged

    Returns:
        The event dictionary with request_id added if available
    """
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add ISO format timestamp to log entries.

    Args:
        logger: The logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary to be logged

    Returns:
        The event dictionary with timestamp added
    """
    from datetime import datetime, timezone

    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def drop_color_message_key(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Remove the color_message key that structlog adds internally.

    Args:
        logger: The logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary to be logged

    Returns:
        The event dictionary without color_message key
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog with appropriate processors and renderers.

    Sets up logging based on environment variables:
    - LOG_LEVEL: The minimum log level (default: INFO)
    - LOG_FORMAT: Output format, 'json' or 'console' (default: json)

    The configuration includes:
    - Timestamp in ISO format
    - Log level normalization
    - Stack info extraction for exceptions
    - Request ID propagation via contextvars
    - Configurable output renderer (JSON or console)
    """
    # Get configuration from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json").lower()

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Define shared processors
    shared_processors: list[Processor] = [
        # Add context from contextvars
        structlog.contextvars.merge_contextvars,
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add custom timestamp
        add_timestamp,
        # Add request ID from contextvar
        add_request_id,
        # Extract stack info on exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exception info
        structlog.processors.format_exc_info,
        # Decode unicode
        structlog.processors.UnicodeDecoder(),
        # Drop color message key
        drop_color_message_key,
    ]

    # Choose renderer based on LOG_FORMAT
    if log_format == "console":
        # Console renderer for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # JSON renderer for production
        renderer = structlog.processors.JSONRenderer()

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            # Prepare event dict for the chosen renderer
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # Use standard library logging as the underlying logger
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances for better performance
        cache_logger_on_first_use=True,
    )

    # Configure the formatter for the standard library logging
    formatter = structlog.stdlib.ProcessorFormatter(
        # These are the processors for the standard library logging
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    # Apply formatter to the root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)


def set_request_id(request_id: str) -> None:
    """
    Set the request ID in the current context.

    This should be called at the beginning of request processing
    to enable request ID propagation through all log entries.

    Args:
        request_id: The unique identifier for the current request
    """
    request_id_var.set(request_id)


def clear_request_id() -> None:
    """
    Clear the request ID from the current context.

    This should be called at the end of request processing
    to prevent ID leakage to subsequent requests.
    """
    request_id_var.set("")


def get_logger(name: str = "") -> structlog.BoundLogger:
    """
    Get a configured structlog logger instance.

    Args:
        name: Optional name for the logger (typically __name__)

    Returns:
        A configured structlog BoundLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info(
        ...     "request_routed",
        ...     model="qwen2.5-72b-instruct-awq",
        ...     machine_id="gpu-server-b",
        ...     latency_ms=15,
        ...     action="forward"
        ... )
    """
    return structlog.get_logger(name)


# Convenience function for backward compatibility
get_structlog_logger = get_logger


if __name__ == "__main__":
    # Demo usage
    configure_logging()

    logger = get_logger(__name__)

    # Example log entries
    logger.info("application_started", component="llm_serve_dashboard")

    # Simulate a request with request ID
    set_request_id("req-12345-abcde")

    logger.info(
        "request_routed",
        model="qwen2.5-72b-instruct-awq",
        machine_id="gpu-server-b",
        latency_ms=15,
        action="forward",
    )

    logger.debug("routing_decision", available_machines=3, selected="gpu-server-b")

    logger.warning(
        "high_latency_detected",
        model="qwen2.5-72b-instruct-awq",
        latency_ms=450,
        threshold_ms=200,
    )

    try:
        # Simulate an error
        raise ValueError("Invalid model configuration")
    except Exception:
        logger.exception(
            "model_configuration_error",
            model="invalid-model",
            error_type="ValueError",
        )

    clear_request_id()

    logger.info("application_shutdown", component="llm_serve_dashboard")
