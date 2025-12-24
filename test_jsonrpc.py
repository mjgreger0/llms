#!/usr/bin/env python3
"""Quick test script to verify JSON-RPC protocol implementation."""

import json
import sys
from pathlib import Path

# Add both dashboard and daemon to path
sys.path.insert(0, str(Path(__file__).parent / "dashboard"))
sys.path.insert(0, str(Path(__file__).parent / "daemon"))

def test_dashboard():
    """Test Dashboard protocol implementation."""
    print("Testing Dashboard protocol...")
    from backend.protocol import (
        ErrorCode,
        build_request,
        build_notification,
        build_response,
        build_error_response,
        parse_message,
        JSONRPCRequest,
        JSONRPCResponse,
        JSONRPCNotification,
        JSONRPCErrorResponse,
    )

    # Test request builder
    req = build_request("container.start", {"model": "llama-70b"})
    assert req["jsonrpc"] == "2.0"
    assert req["method"] == "container.start"
    assert req["params"]["model"] == "llama-70b"
    assert "id" in req
    print(f"  ✓ Request: {json.dumps(req)}")

    # Test notification builder
    notif = build_notification("stats.report", {"cpu": 45.2})
    assert notif["jsonrpc"] == "2.0"
    assert notif["method"] == "stats.report"
    assert "id" not in notif
    print(f"  ✓ Notification: {json.dumps(notif)}")

    # Test response builder
    resp = build_response({"status": "ok"}, 1)
    assert resp["jsonrpc"] == "2.0"
    assert resp["result"]["status"] == "ok"
    assert resp["id"] == 1
    print(f"  ✓ Response: {json.dumps(resp)}")

    # Test error response builder
    err = build_error_response(ErrorCode.METHOD_NOT_FOUND, "Method not found", 1)
    assert err["jsonrpc"] == "2.0"
    assert err["error"]["code"] == -32601
    assert err["id"] == 1
    print(f"  ✓ Error Response: {json.dumps(err)}")

    # Test parser - request
    msg = '{"jsonrpc": "2.0", "method": "ping", "id": 1}'
    parsed = parse_message(msg)
    assert isinstance(parsed, JSONRPCRequest)
    assert parsed.method == "ping"
    print(f"  ✓ Parse Request: {msg}")

    # Test parser - notification
    msg = '{"jsonrpc": "2.0", "method": "stats.report"}'
    parsed = parse_message(msg)
    assert isinstance(parsed, JSONRPCNotification)
    assert parsed.method == "stats.report"
    print(f"  ✓ Parse Notification: {msg}")

    # Test parser - response
    msg = '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    parsed = parse_message(msg)
    assert isinstance(parsed, JSONRPCResponse)
    assert parsed.result == "pong"
    print(f"  ✓ Parse Response: {msg}")

    # Test parser - error handling
    msg = '{"invalid json'
    parsed = parse_message(msg)
    assert isinstance(parsed, JSONRPCErrorResponse)
    assert parsed.error.code == ErrorCode.PARSE_ERROR
    print(f"  ✓ Parse Error: Invalid JSON handled correctly")

    print("Dashboard protocol: ALL TESTS PASSED!\n")


def test_daemon():
    """Test Daemon protocol implementation."""
    print("Testing Daemon protocol...")
    from src.protocol import (
        ErrorCode,
        build_request,
        build_notification,
        build_response,
        build_error_response,
        parse_message,
        JSONRPCRequest,
        JSONRPCResponse,
        JSONRPCNotification,
        JSONRPCErrorResponse,
    )

    # Test request builder
    req = build_request("container.start", {"model": "llama-70b"})
    assert req["jsonrpc"] == "2.0"
    assert req["method"] == "container.start"
    assert req["params"]["model"] == "llama-70b"
    assert "id" in req
    print(f"  ✓ Request: {json.dumps(req)}")

    # Test notification builder
    notif = build_notification("stats.report", {"cpu": 45.2})
    assert notif["jsonrpc"] == "2.0"
    assert notif["method"] == "stats.report"
    assert "id" not in notif
    print(f"  ✓ Notification: {json.dumps(notif)}")

    # Test response builder
    resp = build_response({"status": "ok"}, 1)
    assert resp["jsonrpc"] == "2.0"
    assert resp["result"]["status"] == "ok"
    assert resp["id"] == 1
    print(f"  ✓ Response: {json.dumps(resp)}")

    # Test error response builder
    err = build_error_response(ErrorCode.METHOD_NOT_FOUND, "Method not found", 1)
    assert err["jsonrpc"] == "2.0"
    assert err["error"]["code"] == -32601
    assert err["id"] == 1
    print(f"  ✓ Error Response: {json.dumps(err)}")

    # Test parser - request
    msg = '{"jsonrpc": "2.0", "method": "ping", "id": 1}'
    parsed = parse_message(msg)
    assert isinstance(parsed, JSONRPCRequest)
    assert parsed.method == "ping"
    print(f"  ✓ Parse Request: {msg}")

    # Test parser - notification
    msg = '{"jsonrpc": "2.0", "method": "stats.report"}'
    parsed = parse_message(msg)
    assert isinstance(parsed, JSONRPCNotification)
    assert parsed.method == "stats.report"
    print(f"  ✓ Parse Notification: {msg}")

    # Test parser - response
    msg = '{"jsonrpc": "2.0", "result": "pong", "id": 1}'
    parsed = parse_message(msg)
    assert isinstance(parsed, JSONRPCResponse)
    assert parsed.result == "pong"
    print(f"  ✓ Parse Response: {msg}")

    # Test parser - error handling
    msg = '{"invalid json'
    parsed = parse_message(msg)
    assert isinstance(parsed, JSONRPCErrorResponse)
    assert parsed.error.code == ErrorCode.PARSE_ERROR
    print(f"  ✓ Parse Error: Invalid JSON handled correctly")

    print("Daemon protocol: ALL TESTS PASSED!\n")


if __name__ == "__main__":
    try:
        test_dashboard()
        test_daemon()
        print("=" * 60)
        print("SUCCESS: All JSON-RPC protocol tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
