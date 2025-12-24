"""Logging Configuration - Structured Logging with structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from .config import config


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to the event dict for better filtering."""
    if method_name == "info":
        event_dict["level"] = "INFO"
    elif method_name == "warning":
        event_dict["level"] = "WARNING"
    elif method_name == "error":
        event_dict["level"] = "ERROR"
    elif method_name == "debug":
        event_dict["level"] = "DEBUG"
    elif method_name == "critical":
        event_dict["level"] = "CRITICAL"
    else:
        event_dict["level"] = method_name.upper()
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog based on LOG_LEVEL and LOG_FORMAT from config.

    Sets up structured logging with:
    - JSON renderer for production (LOG_FORMAT=json)
    - Console renderer for development (LOG_FORMAT=console)
    - Timestamp, level, and context fields in all logs
    - Configurable log level filtering
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.LOG_LEVEL),
    )

    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add renderer based on format
    if config.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:  # console format
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Configure logging on module import
configure_logging()

# Export a ready-to-use logger instance
logger = structlog.get_logger("llm-serve-daemon")
