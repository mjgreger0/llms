#!/usr/bin/env python3
"""Test script for timeout calculator implementation."""

import sys
import asyncio

# Add dashboard backend to path
sys.path.insert(0, '/data/home/mgreger/proj/llms/dashboard/backend')

from services.timeout_calculator import (
    ModelSizeTier,
    get_model_size_tier,
    calculate_loading_timeout,
    calculate_inference_timeout,
    extract_param_count_from_name,
    with_timeout,
)


def test_model_size_tier():
    """Test model size tier classification."""
    print("Testing get_model_size_tier...")
    assert get_model_size_tier(1.5) == ModelSizeTier.TINY
    assert get_model_size_tier(7.0) == ModelSizeTier.SMALL
    assert get_model_size_tier(13.0) == ModelSizeTier.MEDIUM
    assert get_model_size_tier(34.0) == ModelSizeTier.LARGE
    assert get_model_size_tier(72.0) == ModelSizeTier.XLARGE
    print("✓ Model size tier tests passed")


def test_loading_timeout():
    """Test loading timeout calculation."""
    print("\nTesting calculate_loading_timeout...")

    # Tiny model
    assert calculate_loading_timeout(1.5) == 60
    assert calculate_loading_timeout(1.5, multi_machine=True) == 180

    # Small model
    assert calculate_loading_timeout(7.0) == 90
    assert calculate_loading_timeout(7.0, multi_machine=True) == 210

    # XLarge model
    assert calculate_loading_timeout(72.0) == 240
    assert calculate_loading_timeout(72.0, multi_machine=True) == 360

    print("✓ Loading timeout tests passed")


def test_inference_timeout():
    """Test inference timeout calculation."""
    print("\nTesting calculate_inference_timeout...")

    # Small model, quick generation
    timeout = calculate_inference_timeout(100, params_billions=7.0, tokens_per_second=30.0)
    assert timeout > 30  # Base timeout
    assert timeout < 40  # Should be quick

    # Large model, longer generation
    timeout = calculate_inference_timeout(1000, params_billions=72.0, tokens_per_second=30.0)
    assert timeout > 100  # Should take longer

    print("✓ Inference timeout tests passed")


def test_param_extraction():
    """Test parameter count extraction from model names."""
    print("\nTesting extract_param_count_from_name...")

    assert extract_param_count_from_name("qwen2.5-72b-instruct") == 72.0
    assert extract_param_count_from_name("llama3.1-8b-chat") == 8.0
    assert extract_param_count_from_name("mistral-7b") == 7.0
    assert extract_param_count_from_name("unknown-model") is None
    assert extract_param_count_from_name("phi-3-mini-4k-instruct") == 3.0

    print("✓ Parameter extraction tests passed")


async def test_with_timeout():
    """Test with_timeout helper."""
    print("\nTesting with_timeout...")

    # Quick task should succeed
    async def quick_task():
        await asyncio.sleep(0.1)
        return "done"

    result = await with_timeout(quick_task(), 1.0, "test_quick")
    assert result == "done"

    # Slow task should timeout
    async def slow_task():
        await asyncio.sleep(2.0)
        return "done"

    try:
        await with_timeout(slow_task(), 0.5, "test_slow")
        assert False, "Should have timed out"
    except asyncio.TimeoutError:
        pass  # Expected

    print("✓ with_timeout tests passed")


def test_router_config():
    """Test router configuration."""
    print("\nTesting RouterConfig...")

    from config import RouterConfig, get_router_config

    # Test default values
    config = RouterConfig()
    assert config.default_loading_timeout == 120
    assert config.default_inference_timeout == 120
    assert config.keepalive_interval == 1.0
    assert config.max_gpus_per_machine == 8
    assert config.max_queue_size == 100

    # Test singleton
    config1 = get_router_config()
    config2 = get_router_config()
    assert config1 is config2

    print("✓ RouterConfig tests passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Phase 5 Tasks 6.1, 6.2, and 6.3 Implementation")
    print("=" * 60)

    try:
        test_model_size_tier()
        test_loading_timeout()
        test_inference_timeout()
        test_param_extraction()
        asyncio.run(test_with_timeout())
        test_router_config()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
