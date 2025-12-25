#!/usr/bin/env python3
"""Quick verification script for container_command.py"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard.backend.services.container_command import (
    ContainerCommandGenerator,
    PortAllocator,
)
from dashboard.backend.models.database import ContainerConfig, Model, ModelQuantization


async def main():
    """Run basic verification tests."""
    print("Testing PortAllocator...")

    # Test port allocator
    allocator = PortAllocator(min_port=8001, max_port=8999)
    port1 = await allocator.allocate()
    print(f"  Allocated port: {port1}")
    assert 8001 <= port1 <= 8999, "Port out of range"

    port2 = await allocator.allocate()
    print(f"  Allocated port: {port2}")
    assert port1 != port2, "Ports should be unique"

    await allocator.release(port1)
    allocated = await allocator.get_allocated()
    assert port1 not in allocated, "Port should be released"
    assert port2 in allocated, "Port should still be allocated"
    print("  PortAllocator: PASS\n")

    # Test command generator
    print("Testing ContainerCommandGenerator...")

    # Create test objects
    model = Model()
    model.id = 1
    model.name = "test-model"
    model.provider = "Test"

    quant = ModelQuantization()
    quant.id = 1
    quant.model_id = 1
    quant.quantization = "awq"
    quant.file_path = "test-model-awq"
    quant.gpu_count = 1

    config = ContainerConfig()
    config.id = 1
    config.model_quant_id = 1
    config.runtime = "vllm"
    config.context_length = 8192
    config.max_parallel = 4
    config.tensor_parallel = 1
    config.pipeline_parallel = 1
    config.extra_args = {}

    generator = ContainerCommandGenerator(
        port_allocator=allocator,
        model_path="/test/models"
    )

    # Test vLLM command generation
    cmd = await generator.generate(config, quant, model, [0], 8001)
    print(f"  Generated command with {len(cmd)} arguments")

    # Verify basic structure
    assert cmd[0] == "podman", "Should start with podman"
    assert "run" in cmd, "Should have run command"
    assert "--device" in cmd, "Should have GPU device"
    assert "--model" in cmd, "Should have model path"
    print("  Command structure: PASS\n")

    # Test GPU device formatting
    print("Testing GPU device formatting...")
    devices = generator._format_gpu_devices([0, 1, 2])
    assert devices == [
        "--device", "nvidia.com/gpu=0",
        "--device", "nvidia.com/gpu=1",
        "--device", "nvidia.com/gpu=2"
    ], "Device formatting incorrect"
    print("  GPU device formatting: PASS\n")

    # Test environment args
    print("Testing environment args...")
    env_args = generator._build_env_args({"TEST": "value"}, [0, 1])
    assert "-e" in env_args, "Should have -e flag"
    assert "CUDA_VISIBLE_DEVICES=0,1" in env_args, "Should have CUDA_VISIBLE_DEVICES"
    assert "TEST=value" in env_args, "Should have custom env var"
    print("  Environment args: PASS\n")

    # Test labels
    print("Testing label building...")
    labels = generator._build_label_args("test-model-awq", "vllm", [0])
    assert "--label" in labels, "Should have label flag"
    assert "llm-serve=true" in labels, "Should have llm-serve label"
    assert "model=test-model-awq" in labels, "Should have model label"
    assert "runtime=vllm" in labels, "Should have runtime label"
    print("  Label building: PASS\n")

    # Test container name
    print("Testing container name generation...")
    name = generator._container_name("test-model", "awq")
    assert name.startswith("vllm-test-model-awq-"), "Name should have correct prefix"
    assert len(name.split("-")[-1]) == 8, "Should have 8-char random suffix"
    print(f"  Generated name: {name}")
    print("  Container name: PASS\n")

    # Test unknown runtime
    print("Testing unknown runtime...")
    config.runtime = "unknown"
    try:
        await generator.generate(config, quant, model, [0], 8001)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "Unknown runtime" in str(e), "Should have correct error message"
        print("  Unknown runtime error: PASS\n")

    # Test SGLang not implemented
    print("Testing SGLang not implemented...")
    config.runtime = "sglang"
    try:
        await generator.generate(config, quant, model, [0], 8001)
        assert False, "Should raise NotImplementedError"
    except NotImplementedError as e:
        assert "sglang not yet implemented" in str(e), "Should have correct error message"
        print("  SGLang not implemented: PASS\n")

    # Test llama.cpp not implemented
    print("Testing llama.cpp not implemented...")
    config.runtime = "llamacpp"
    try:
        await generator.generate(config, quant, model, [0], 8001)
        assert False, "Should raise NotImplementedError"
    except NotImplementedError as e:
        assert "llamacpp not yet implemented" in str(e), "Should have correct error message"
        print("  llama.cpp not implemented: PASS\n")

    print("All verification tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
