#!/usr/bin/env python3
"""Basic verification script for QueueManager implementation.

This script verifies that:
1. The module can be imported without errors
2. Classes can be instantiated
3. Basic methods are accessible
"""

import asyncio
import sys
from datetime import datetime

# Add dashboard backend to path
sys.path.insert(0, '/data/home/mgreger/proj/llms/dashboard/backend')

from services.queue_manager import QueueManager, RequestContext


async def verify_queue_manager():
    """Verify basic QueueManager functionality."""
    print("Testing QueueManager implementation...")

    # Test 1: Instantiation
    print("\n1. Testing instantiation...")
    qm = QueueManager()
    print("   ✓ QueueManager instantiated successfully")

    # Test 2: RequestContext creation
    print("\n2. Testing RequestContext creation...")
    ctx = RequestContext(
        request_id="test-001",
        model="qwen2.5-72b",
        quantization="awq",
        timeout=120.0
    )
    print(f"   ✓ RequestContext created: {ctx.request_id}")

    # Test 3: Queue creation
    print("\n3. Testing queue creation...")
    queue = await qm.get_or_create_queue("qwen2.5-72b-awq")
    print(f"   ✓ Queue created for qwen2.5-72b-awq")

    # Test 4: Enqueue
    print("\n4. Testing enqueue...")
    ctx1 = RequestContext(
        request_id="req-001",
        model="qwen2.5-72b",
        quantization="awq"
    )
    await qm.enqueue("qwen2.5-72b-awq", ctx1)
    print(f"   ✓ Request {ctx1.request_id} enqueued")

    # Test 5: Queue status
    print("\n5. Testing queue status...")
    status = qm.get_queue_status()
    print(f"   ✓ Status: {status}")

    # Test 6: Active count tracking
    print("\n6. Testing active count tracking...")
    print(f"   Active count: {qm._active_counts.get('qwen2.5-72b-awq', 0)}")
    print(f"   Is idle: {qm.is_idle('qwen2.5-72b-awq')}")

    # Test 7: Dequeue
    print("\n7. Testing dequeue...")
    ctx_dequeued = await qm.dequeue("qwen2.5-72b-awq")
    print(f"   ✓ Request {ctx_dequeued.request_id} dequeued")

    # Test 8: LRU tracking
    print("\n8. Testing LRU tracking...")
    qm.decrement_active("qwen2.5-72b-awq")
    qm.update_last_used("qwen2.5-72b-awq")
    print(f"   Is idle now: {qm.is_idle('qwen2.5-72b-awq')}")
    lru_models = qm.get_lru_idle_models()
    print(f"   ✓ LRU idle models: {lru_models}")

    # Test 9: Multiple queues
    print("\n9. Testing multiple queues...")
    ctx2 = RequestContext(
        request_id="req-002",
        model="llama3.1-70b",
        quantization="fp8"
    )
    await qm.enqueue("llama3.1-70b-fp8", ctx2)
    status = qm.get_queue_status()
    print(f"   ✓ Multiple queues status: {status}")

    # Test 10: Context manager
    print("\n10. Testing track_request context manager...")
    async with qm.track_request("llama3.1-70b-fp8"):
        print("   ✓ Inside track_request context")
    print(f"   ✓ Context manager executed, active count: {qm._active_counts.get('llama3.1-70b-fp8', 0)}")

    print("\n" + "="*60)
    print("All tests passed! ✓")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(verify_queue_manager())
