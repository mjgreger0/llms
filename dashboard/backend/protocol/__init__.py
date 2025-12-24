"""JSON-RPC 2.0 protocol implementation for LLM Serve Dashboard."""

from .jsonrpc import (
    ErrorCode,
    JSONRPCError,
    JSONRPCErrorResponse,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    build_error_response,
    build_notification,
    build_request,
    build_response,
    parse_message,
)

__all__ = [
    # Error codes
    "ErrorCode",
    # Message types
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCNotification",
    "JSONRPCError",
    "JSONRPCErrorResponse",
    # Builders
    "build_request",
    "build_response",
    "build_notification",
    "build_error_response",
    # Parser
    "parse_message",
]
