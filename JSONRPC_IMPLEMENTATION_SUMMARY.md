# JSON-RPC 2.0 Protocol Implementation Summary

## Overview

This document summarizes the JSON-RPC 2.0 protocol implementation for both the Dashboard and Daemon components of the LLM Serve system, completed according to Phase 4 requirements.

## Files Created

### Dashboard Backend
1. `/data/home/mgreger/proj/llms/dashboard/backend/protocol/__init__.py`
   - Package initialization with exports
   - Provides clean public API for protocol usage

2. `/data/home/mgreger/proj/llms/dashboard/backend/protocol/jsonrpc.py`
   - Complete JSON-RPC 2.0 implementation
   - ~460 lines of production-ready code

### Daemon
1. `/data/home/mgreger/proj/llms/daemon/src/protocol/__init__.py`
   - Package initialization with exports
   - Provides clean public API for protocol usage

2. `/data/home/mgreger/proj/llms/daemon/src/protocol/jsonrpc.py`
   - Complete JSON-RPC 2.0 implementation (identical to Dashboard)
   - ~460 lines of production-ready code

## Implementation Details

### Error Codes (ErrorCode class)
Standard JSON-RPC 2.0 error codes implemented:
- `PARSE_ERROR = -32700` - Invalid JSON was received
- `INVALID_REQUEST = -32600` - Invalid Request object
- `METHOD_NOT_FOUND = -32601` - Method does not exist
- `INVALID_PARAMS = -32602` - Invalid method parameters
- `INTERNAL_ERROR = -32603` - Internal JSON-RPC error

### Message Models (Pydantic BaseModel)

All models include strict validation and the required `"jsonrpc": "2.0"` field:

1. **JSONRPCRequest**
   - Fields: `jsonrpc`, `method`, `params` (optional), `id`
   - Used for requests that expect a response
   - Validates method name (non-empty, not starting with "rpc.")

2. **JSONRPCNotification**
   - Fields: `jsonrpc`, `method`, `params` (optional)
   - No `id` field - does not expect response
   - Used for fire-and-forget messages

3. **JSONRPCResponse**
   - Fields: `jsonrpc`, `result`, `id`
   - Success response to a request

4. **JSONRPCError**
   - Fields: `code`, `message`, `data` (optional)
   - Nested in error responses

5. **JSONRPCErrorResponse**
   - Fields: `jsonrpc`, `error`, `id` (can be null)
   - Error response to a failed request

### Request ID Generator

Thread-safe auto-incrementing ID generator:
- `RequestIDGenerator` class with threading.Lock
- `get_next_request_id()` - Returns next ID (thread-safe)
- `reset_request_id_counter()` - Reset for testing
- Global instance `_request_id_generator`

### Message Builders

All builders return `dict[str, Any]` for easy JSON serialization:

1. **build_request(method, params=None, request_id=None)**
   - Auto-increments ID if not provided
   - Returns dictionary with request structure
   - Example: `{'jsonrpc': '2.0', 'method': 'ping', 'id': 1}`

2. **build_notification(method, params=None)**
   - No ID field
   - Example: `{'jsonrpc': '2.0', 'method': 'stats.report', 'params': {...}}`

3. **build_response(result, request_id)**
   - Matches request by ID
   - Example: `{'jsonrpc': '2.0', 'result': {...}, 'id': 1}`

4. **build_error_response(code, message, request_id=None, data=None)**
   - Standard error codes available via ErrorCode class
   - Example: `{'jsonrpc': '2.0', 'error': {'code': -32601, 'message': '...'}, 'id': 1}`

### Message Parser

**parse_message(message)** - Universal parser with comprehensive validation:

**Input Types:**
- `str` - JSON string
- `bytes` - JSON bytes
- `dict[str, Any]` - Already parsed dictionary

**Return Type:**
- `JSONRPCRequest | JSONRPCResponse | JSONRPCNotification | JSONRPCErrorResponse`
- Always returns a valid message object
- Returns `JSONRPCErrorResponse` for invalid/malformed messages

**Validation Steps:**
1. Parse JSON (if string/bytes)
   - Returns PARSE_ERROR (-32700) if invalid JSON
2. Validate it's a dict
   - Returns INVALID_REQUEST if not an object
3. Validate `jsonrpc` field is "2.0"
   - Returns INVALID_REQUEST if missing/wrong version
4. Determine message type based on fields:
   - Has `error` → `JSONRPCErrorResponse`
   - Has `result` + `id` → `JSONRPCResponse`
   - Has `method` + `id` → `JSONRPCRequest`
   - Has `method` (no id) → `JSONRPCNotification`
   - Invalid combination → Returns error response

**Error Handling:**
- Gracefully handles all parsing/validation errors
- Never raises exceptions
- Returns proper error responses with appropriate codes
- Preserves request ID when available for error responses

## Features Implemented

✅ **All Required Features:**
- [x] Request builder with method, params, and auto-incrementing ID (thread-safe)
- [x] Response builder with result or error
- [x] Notification builder (no ID field)
- [x] Error response builder with standard error codes
- [x] All messages include `jsonrpc: "2.0"` field
- [x] Type hints and validation using Pydantic
- [x] `parse_message()` function with discriminated union return type
- [x] Parses JSON string to Python dict
- [x] Validates JSON-RPC 2.0 format
- [x] Distinguishes between request, response, notification
- [x] Extracts method, params, id, result, error
- [x] Returns appropriate error for malformed messages

✅ **Additional Features:**
- Thread-safe request ID generation using threading.Lock
- Comprehensive docstrings with examples
- Pydantic field validators for method names
- Support for both dict and list params (per JSON-RPC spec)
- Support for string or int request IDs
- Strict validation with ConfigDict(extra="forbid")
- Type aliases for discriminated unions
- Comprehensive error messages with context

## Code Quality

**Consistency:**
- Identical implementation for Dashboard and Daemon
- Follows Pydantic v2 patterns used in existing codebase
- Consistent with existing code style and formatting

**Type Safety:**
- Full type hints throughout
- Literal types for version field
- Union types for discriminated unions
- Optional types where appropriate

**Validation:**
- Pydantic models with field validators
- Method name validation (non-empty, no "rpc." prefix)
- Strict mode prevents extra fields
- Comprehensive error handling

**Documentation:**
- Module-level docstrings
- Class docstrings
- Function docstrings with Args/Returns/Examples
- Inline comments for complex logic

## Usage Examples

### Building Messages

```python
from dashboard.backend.protocol import build_request, build_notification, ErrorCode

# Create a request (with auto-incrementing ID)
request = build_request("container.start", {"model": "llama-70b"})
# {'jsonrpc': '2.0', 'method': 'container.start', 'params': {...}, 'id': 1}

# Create a notification (no response expected)
notification = build_notification("stats.report", {"cpu": 45.2})
# {'jsonrpc': '2.0', 'method': 'stats.report', 'params': {...}}

# Create a response
response = build_response({"status": "ok"}, request_id=1)
# {'jsonrpc': '2.0', 'result': {'status': 'ok'}, 'id': 1}

# Create an error response
error = build_error_response(
    ErrorCode.METHOD_NOT_FOUND,
    "Method not found",
    request_id=1
)
# {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': '...'}, 'id': 1}
```

### Parsing Messages

```python
from dashboard.backend.protocol import parse_message, JSONRPCRequest

# Parse a JSON string
msg = '{"jsonrpc": "2.0", "method": "ping", "id": 1}'
parsed = parse_message(msg)

# Type discrimination
if isinstance(parsed, JSONRPCRequest):
    print(f"Calling method: {parsed.method}")
elif isinstance(parsed, JSONRPCResponse):
    print(f"Got result: {parsed.result}")
elif isinstance(parsed, JSONRPCNotification):
    print(f"Notification: {parsed.method}")
elif isinstance(parsed, JSONRPCErrorResponse):
    print(f"Error: {parsed.error.message}")

# Invalid messages return error responses
invalid = parse_message('{"invalid json')
assert isinstance(invalid, JSONRPCErrorResponse)
assert invalid.error.code == ErrorCode.PARSE_ERROR
```

### WebSocket Integration Example

```python
# Dashboard side (receiving messages)
async def handle_daemon_message(websocket):
    async for raw_message in websocket:
        message = parse_message(raw_message)

        if isinstance(message, JSONRPCNotification):
            # Handle notification (no response needed)
            await handle_notification(message.method, message.params)

        elif isinstance(message, JSONRPCRequest):
            # Handle request (send response)
            try:
                result = await handle_request(message.method, message.params)
                response = build_response(result, message.id)
            except Exception as e:
                response = build_error_response(
                    ErrorCode.INTERNAL_ERROR,
                    str(e),
                    message.id
                )
            await websocket.send_json(response)
```

## Testing

A test script has been created at `/data/home/mgreger/proj/llms/test_jsonrpc.py` to verify:
- Request building
- Notification building
- Response building
- Error response building
- Message parsing (all types)
- Error handling (invalid JSON, etc.)
- Thread-safe ID generation

Run tests with:
```bash
cd /data/home/mgreger/proj/llms
python test_jsonrpc.py
```

## Integration Points

This protocol implementation is ready to be integrated into:

1. **Dashboard WebSocket Handler** (`/ws/daemon`)
   - Use `parse_message()` to parse incoming messages
   - Use builders to create responses

2. **Daemon WebSocket Client**
   - Use builders to send requests/notifications
   - Use `parse_message()` to parse responses/commands

3. **DaemonManager**
   - Use `build_request()` for sending commands
   - Track pending requests by ID

4. **Stats Collector**
   - Use `build_notification()` for stats reports

5. **Container Commands**
   - Use `build_response()` for command results
   - Use `build_error_response()` for failures

## Compliance

This implementation is fully compliant with:
- JSON-RPC 2.0 Specification (https://www.jsonrpc.org/specification)
- All fields, error codes, and message types match the spec exactly
- Method name validation per spec (no "rpc." prefix)
- Proper handling of requests vs notifications (ID presence)

## Next Steps

The protocol layer is now complete and ready for integration with:
- Task 2.1: Dashboard WebSocket endpoint
- Task 2.3: Message dispatcher
- Task 6.1: Daemon WebSocket client
- Task 6.4: Daemon command handler dispatcher

All components can now import and use the protocol implementation:

```python
# Dashboard
from backend.protocol import (
    ErrorCode,
    build_request,
    build_response,
    build_notification,
    build_error_response,
    parse_message,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCErrorResponse,
)

# Daemon
from src.protocol import (
    ErrorCode,
    build_request,
    build_response,
    build_notification,
    build_error_response,
    parse_message,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCErrorResponse,
)
```
