#!/usr/bin/env python3
"""Simple test script for SSE utilities."""

import asyncio
import sys
from pathlib import Path

# Add dashboard backend to path
sys.path.insert(0, str(Path(__file__).parent / "dashboard" / "backend"))

from services.sse_utils import (
    format_sse_data,
    format_sse_comment,
    create_error_chunk,
    sse_generator,
    keepalive_generator,
    stream_with_keepalive,
)


async def test_format_functions():
    """Test basic formatting functions."""
    print("=== Testing Format Functions ===")

    # Test format_sse_data with dict
    result = format_sse_data({"content": "hello"})
    print(f"format_sse_data(dict): {repr(result)}")
    assert result == 'data: {"content": "hello"}\n\n'

    # Test format_sse_data with string
    result = format_sse_data("hello")
    print(f"format_sse_data(str): {repr(result)}")
    assert result == 'data: hello\n\n'

    # Test format_sse_comment
    result = format_sse_comment("loading model")
    print(f"format_sse_comment: {repr(result)}")
    assert result == ': loading model\n\n'

    # Test create_error_chunk
    result = create_error_chunk("Something went wrong", "test_error")
    print(f"create_error_chunk: {repr(result)}")
    assert "error" in result
    assert "Something went wrong" in result

    print("✓ All format functions passed\n")


async def test_sse_generator():
    """Test SSE generator."""
    print("=== Testing SSE Generator ===")

    async def data_source():
        yield {"id": 1, "content": "hello"}
        yield {"id": 2, "content": "world"}
        yield ": comment"
        yield "plain string"

    chunks = []
    async for chunk in sse_generator(data_source()):
        print(f"Chunk: {repr(chunk)}")
        chunks.append(chunk)

    assert len(chunks) == 5  # 4 items + [DONE]
    assert chunks[0] == 'data: {"id": 1, "content": "hello"}\n\n'
    assert chunks[1] == 'data: {"id": 2, "content": "world"}\n\n'
    assert chunks[2] == ': comment\n\n'
    assert chunks[3] == 'data: plain string\n\n'
    assert chunks[4] == 'data: [DONE]\n\n'

    print("✓ SSE generator passed\n")


async def test_keepalive_generator():
    """Test keepalive generator."""
    print("=== Testing Keepalive Generator ===")

    loading_event = asyncio.Event()

    # Create task that sets event after 2 seconds
    async def set_event_later():
        await asyncio.sleep(2)
        loading_event.set()

    asyncio.create_task(set_event_later())

    chunks = []
    start = asyncio.get_event_loop().time()

    async for chunk in keepalive_generator(
        loading_event,
        "test-model",
        estimated_seconds=10,
        interval=0.5
    ):
        elapsed = asyncio.get_event_loop().time() - start
        print(f"[{elapsed:.1f}s] Keepalive: {repr(chunk)}")
        chunks.append(chunk)

        if len(chunks) >= 5:  # Safety limit
            break

    assert len(chunks) >= 3  # Should get several keepalive messages
    assert all("loading test-model" in chunk for chunk in chunks)
    assert all("remaining" in chunk for chunk in chunks)

    print("✓ Keepalive generator passed\n")


async def test_stream_with_keepalive():
    """Test stream with keepalive integration."""
    print("=== Testing Stream with Keepalive ===")

    loading_event = asyncio.Event()

    # Simulate loading task
    async def load_model():
        await asyncio.sleep(1.5)
        loading_event.set()

    loading_task = asyncio.create_task(load_model())

    # Response generator after loading
    async def response_generator():
        yield 'data: {"content": "Response chunk 1"}\n\n'
        yield 'data: {"content": "Response chunk 2"}\n\n'

    chunks = []
    async for chunk in stream_with_keepalive(
        loading_task,
        loading_event,
        response_generator(),
        "test-model",
        estimated_load_seconds=10
    ):
        print(f"Stream chunk: {repr(chunk[:50])}...")
        chunks.append(chunk)

    # Should have some keepalive messages followed by response chunks
    assert len(chunks) >= 2

    # Check that we got both keepalive and response chunks
    keepalive_chunks = [c for c in chunks if "loading test-model" in c]
    response_chunks = [c for c in chunks if "Response chunk" in c]

    assert len(keepalive_chunks) >= 1, "Should have at least one keepalive"
    assert len(response_chunks) == 2, "Should have two response chunks"

    print("✓ Stream with keepalive passed\n")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("SSE Utilities Test Suite")
    print("="*60 + "\n")

    try:
        await test_format_functions()
        await test_sse_generator()
        await test_keepalive_generator()
        await test_stream_with_keepalive()

        print("="*60)
        print("✓ All tests passed!")
        print("="*60 + "\n")
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
