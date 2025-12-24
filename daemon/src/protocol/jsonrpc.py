"""
JSON-RPC 2.0 protocol implementation.

This module provides builders and parsers for JSON-RPC 2.0 messages according to
the JSON-RPC 2.0 specification: https://www.jsonrpc.org/specification

All messages include the "jsonrpc": "2.0" field as required by the spec.
"""

import json
import threading
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Standard JSON-RPC Error Codes
# ============================================================================

class ErrorCode:
    """Standard JSON-RPC 2.0 error codes."""

    PARSE_ERROR = -32700
    """Invalid JSON was received by the server."""

    INVALID_REQUEST = -32600
    """The JSON sent is not a valid Request object."""

    METHOD_NOT_FOUND = -32601
    """The method does not exist / is not available."""

    INVALID_PARAMS = -32602
    """Invalid method parameter(s)."""

    INTERNAL_ERROR = -32603
    """Internal JSON-RPC error."""


# ============================================================================
# JSON-RPC Message Models
# ============================================================================

class JSONRPCError(BaseModel):
    """JSON-RPC error object."""

    code: int = Field(..., description="Error code indicating the error type")
    message: str = Field(..., description="Short description of the error")
    data: Optional[Any] = Field(None, description="Additional error information")

    model_config = ConfigDict(extra="forbid")


class JSONRPCRequest(BaseModel):
    """
    JSON-RPC request message.

    A request expects a response from the server.
    """

    jsonrpc: Literal["2.0"] = Field("2.0", description="JSON-RPC protocol version")
    method: str = Field(..., description="Method name to invoke")
    params: Optional[Union[dict[str, Any], list[Any]]] = Field(
        None,
        description="Method parameters (object or array)"
    )
    id: Union[str, int] = Field(..., description="Request ID for matching response")

    model_config = ConfigDict(extra="forbid")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Ensure method name is not empty and doesn't start with 'rpc.'"""
        if not v:
            raise ValueError("method cannot be empty")
        if v.startswith("rpc."):
            raise ValueError("method names starting with 'rpc.' are reserved")
        return v


class JSONRPCNotification(BaseModel):
    """
    JSON-RPC notification message.

    A notification is a request that does not expect a response.
    """

    jsonrpc: Literal["2.0"] = Field("2.0", description="JSON-RPC protocol version")
    method: str = Field(..., description="Method name to invoke")
    params: Optional[Union[dict[str, Any], list[Any]]] = Field(
        None,
        description="Method parameters (object or array)"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Ensure method name is not empty and doesn't start with 'rpc.'"""
        if not v:
            raise ValueError("method cannot be empty")
        if v.startswith("rpc."):
            raise ValueError("method names starting with 'rpc.' are reserved")
        return v


class JSONRPCResponse(BaseModel):
    """
    JSON-RPC success response message.

    Contains the result of a successful request.
    """

    jsonrpc: Literal["2.0"] = Field("2.0", description="JSON-RPC protocol version")
    result: Any = Field(..., description="Result of the method invocation")
    id: Union[str, int] = Field(..., description="ID matching the original request")

    model_config = ConfigDict(extra="forbid")


class JSONRPCErrorResponse(BaseModel):
    """
    JSON-RPC error response message.

    Contains an error from a failed request.
    """

    jsonrpc: Literal["2.0"] = Field("2.0", description="JSON-RPC protocol version")
    error: JSONRPCError = Field(..., description="Error object describing the failure")
    id: Union[str, int, None] = Field(..., description="ID matching the original request (or null)")

    model_config = ConfigDict(extra="forbid")


# Type alias for any JSON-RPC message
JSONRPCMessage = Union[
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCErrorResponse,
]


# ============================================================================
# Request ID Generator (Thread-Safe)
# ============================================================================

class RequestIDGenerator:
    """Thread-safe auto-incrementing request ID generator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counter = 0

    def next_id(self) -> int:
        """Get the next request ID."""
        with self._lock:
            self._counter += 1
            return self._counter

    def reset(self) -> None:
        """Reset the counter to 0 (primarily for testing)."""
        with self._lock:
            self._counter = 0


# Global request ID generator instance
_request_id_generator = RequestIDGenerator()


def get_next_request_id() -> int:
    """Get the next auto-incrementing request ID (thread-safe)."""
    return _request_id_generator.next_id()


def reset_request_id_counter() -> None:
    """Reset the request ID counter to 0 (primarily for testing)."""
    _request_id_generator.reset()


# ============================================================================
# Message Builders
# ============================================================================

def build_request(
    method: str,
    params: Optional[Union[dict[str, Any], list[Any]]] = None,
    request_id: Optional[Union[str, int]] = None,
) -> dict[str, Any]:
    """
    Build a JSON-RPC 2.0 request message.

    Args:
        method: The method name to invoke
        params: Optional method parameters (dict or list)
        request_id: Optional request ID. If not provided, auto-increments.

    Returns:
        Dictionary containing the JSON-RPC request

    Examples:
        >>> build_request("container.start", {"model": "llama-70b"})
        {'jsonrpc': '2.0', 'method': 'container.start', 'params': {'model': 'llama-70b'}, 'id': 1}

        >>> build_request("ping")
        {'jsonrpc': '2.0', 'method': 'ping', 'id': 2}
    """
    if request_id is None:
        request_id = get_next_request_id()

    request = JSONRPCRequest(
        method=method,
        params=params,
        id=request_id,
    )

    return request.model_dump(exclude_none=True)


def build_notification(
    method: str,
    params: Optional[Union[dict[str, Any], list[Any]]] = None,
) -> dict[str, Any]:
    """
    Build a JSON-RPC 2.0 notification message.

    Notifications are requests that do not expect a response.
    They do not have an 'id' field.

    Args:
        method: The method name to invoke
        params: Optional method parameters (dict or list)

    Returns:
        Dictionary containing the JSON-RPC notification

    Examples:
        >>> build_notification("stats.report", {"cpu": 45.2, "memory": 78.1})
        {'jsonrpc': '2.0', 'method': 'stats.report', 'params': {'cpu': 45.2, 'memory': 78.1}}

        >>> build_notification("daemon.register")
        {'jsonrpc': '2.0', 'method': 'daemon.register'}
    """
    notification = JSONRPCNotification(
        method=method,
        params=params,
    )

    return notification.model_dump(exclude_none=True)


def build_response(
    result: Any,
    request_id: Union[str, int],
) -> dict[str, Any]:
    """
    Build a JSON-RPC 2.0 success response message.

    Args:
        result: The result of the method invocation
        request_id: The ID from the original request

    Returns:
        Dictionary containing the JSON-RPC response

    Examples:
        >>> build_response({"status": "ok"}, 1)
        {'jsonrpc': '2.0', 'result': {'status': 'ok'}, 'id': 1}

        >>> build_response([1, 2, 3], "req-123")
        {'jsonrpc': '2.0', 'result': [1, 2, 3], 'id': 'req-123'}
    """
    response = JSONRPCResponse(
        result=result,
        id=request_id,
    )

    return response.model_dump()


def build_error_response(
    code: int,
    message: str,
    request_id: Union[str, int, None] = None,
    data: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Build a JSON-RPC 2.0 error response message.

    Args:
        code: Error code (use ErrorCode constants for standard errors)
        message: Human-readable error message
        request_id: The ID from the original request (or None if request had no ID)
        data: Optional additional error information

    Returns:
        Dictionary containing the JSON-RPC error response

    Examples:
        >>> build_error_response(ErrorCode.METHOD_NOT_FOUND, "Method not found", 1)
        {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': 'Method not found'}, 'id': 1}

        >>> build_error_response(
        ...     ErrorCode.INVALID_PARAMS,
        ...     "Missing required parameter",
        ...     "req-123",
        ...     {"missing": "model"}
        ... )
        {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': 'Missing required parameter', 'data': {'missing': 'model'}}, 'id': 'req-123'}
    """
    error = JSONRPCError(
        code=code,
        message=message,
        data=data,
    )

    error_response = JSONRPCErrorResponse(
        error=error,
        id=request_id,
    )

    return error_response.model_dump(exclude_none=True)


# ============================================================================
# Message Parser
# ============================================================================

def parse_message(
    message: Union[str, bytes, dict[str, Any]],
) -> Union[JSONRPCMessage, JSONRPCErrorResponse]:
    """
    Parse a JSON-RPC 2.0 message from JSON string, bytes, or dict.

    This function validates the message structure and returns the appropriate
    message type (Request, Response, Notification, or ErrorResponse).

    If the message is malformed or invalid, it returns a JSONRPCErrorResponse
    with the appropriate error code.

    Args:
        message: JSON string, bytes, or dict containing the message

    Returns:
        Parsed message object or error response if parsing fails

    Examples:
        >>> msg = '{"jsonrpc": "2.0", "method": "ping", "id": 1}'
        >>> result = parse_message(msg)
        >>> isinstance(result, JSONRPCRequest)
        True

        >>> msg = '{"jsonrpc": "2.0", "method": "stats.report"}'
        >>> result = parse_message(msg)
        >>> isinstance(result, JSONRPCNotification)
        True

        >>> msg = '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
        >>> result = parse_message(msg)
        >>> isinstance(result, JSONRPCResponse)
        True

        >>> msg = '{"invalid json'
        >>> result = parse_message(msg)
        >>> isinstance(result, JSONRPCErrorResponse)
        True
        >>> result.error.code == ErrorCode.PARSE_ERROR
        True
    """
    # Step 1: Parse JSON if needed
    if isinstance(message, (str, bytes)):
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            # Parse error - invalid JSON
            return JSONRPCErrorResponse(
                error=JSONRPCError(
                    code=ErrorCode.PARSE_ERROR,
                    message="Parse error",
                    data=str(e),
                ),
                id=None,
            )
    else:
        data = message

    # Step 2: Ensure it's a dict
    if not isinstance(data, dict):
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=ErrorCode.INVALID_REQUEST,
                message="Invalid Request",
                data="Message must be a JSON object",
            ),
            id=None,
        )

    # Step 3: Validate JSON-RPC version
    if data.get("jsonrpc") != "2.0":
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=ErrorCode.INVALID_REQUEST,
                message="Invalid Request",
                data="Missing or invalid 'jsonrpc' field (must be '2.0')",
            ),
            id=data.get("id"),
        )

    # Step 4: Determine message type and parse
    has_method = "method" in data
    has_result = "result" in data
    has_error = "error" in data
    has_id = "id" in data

    try:
        # Error response (has 'error' field)
        if has_error:
            return JSONRPCErrorResponse.model_validate(data)

        # Success response (has 'result' field and 'id')
        if has_result:
            if not has_id:
                return JSONRPCErrorResponse(
                    error=JSONRPCError(
                        code=ErrorCode.INVALID_REQUEST,
                        message="Invalid Request",
                        data="Response must have 'id' field",
                    ),
                    id=None,
                )
            return JSONRPCResponse.model_validate(data)

        # Request (has 'method' and 'id')
        if has_method and has_id:
            return JSONRPCRequest.model_validate(data)

        # Notification (has 'method' but no 'id')
        if has_method and not has_id:
            return JSONRPCNotification.model_validate(data)

        # Invalid - doesn't match any message type
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=ErrorCode.INVALID_REQUEST,
                message="Invalid Request",
                data="Message must have either 'method', 'result', or 'error'",
            ),
            id=data.get("id"),
        )

    except Exception as e:
        # Validation error - invalid request structure
        return JSONRPCErrorResponse(
            error=JSONRPCError(
                code=ErrorCode.INVALID_REQUEST,
                message="Invalid Request",
                data=str(e),
            ),
            id=data.get("id"),
        )
