"""Request middleware for LLM Serve Dashboard.

Provides request ID generation, request logging, and timing middleware
for FastAPI applications using Starlette middleware patterns.
"""

import contextvars
import time
import uuid
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for storing request ID
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)

logger = structlog.get_logger(__name__)


def get_request_id() -> str:
    """Get the current request ID from context.

    Returns:
        str: The current request ID, or empty string if not set.
    """
    return request_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and manage request context.

    Generates a unique request ID (UUID) for each request and stores it
    in contextvars for access throughout the request lifecycle.
    Adds X-Request-ID header to the response.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and inject request ID into context.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            Response: The HTTP response with X-Request-ID header.
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Store in context variable
        request_id_ctx.set(request_id)

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging.

    Logs request start and completion with method, path, status code,
    and duration. Uses structlog for structured logging output.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Log request start and completion.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            Response: The HTTP response.
        """
        # Get request ID from context
        request_id = get_request_id()

        # Log request start
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
            client_host=request.client.host if request.client else None,
        )

        # Track start time
        start_time = time.perf_counter()

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log error and re-raise
            duration = time.perf_counter() - start_time
            logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
                exc_info=True,
            )
            raise

        # Calculate duration
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 2)

        # Log request completion
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track and report request timing.

    Measures request duration and adds X-Response-Time header
    with the duration in milliseconds.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Track request timing and add response header.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            Response: The HTTP response with X-Response-Time header.
        """
        # Track start time
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration in milliseconds
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 2)

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response
