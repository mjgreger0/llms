"""
Tests for ContainerCommandGenerator service (Phase 7).

Tests command generation for vLLM containers including GPU allocation,
port management, environment variables, and labels.
"""

import asyncio
import json

import pytest
import pytest_asyncio

from dashboard.backend.models.database import ContainerConfig, Model, ModelQuantization
from dashboard.backend.services.container_command import (
    ContainerCommandGenerator,
    PortAllocator,
)


@pytest_asyncio.fixture
async def port_allocator():
    """Create a fresh port allocator for each test."""
    return PortAllocator(min_port=8001, max_port=8999)


@pytest.fixture
def sample_model():
    """Create a sample Model instance."""
    model = Model()
    model.id = 1
    model.name = "qwen2.5-72b-instruct"
    model.provider = "Qwen"
    model.huggingface_id = "Qwen/Qwen2.5-72B-Instruct"
    model.base_parameters = "72B"
    return model


@pytest.fixture
def sample_model_quant():
    """Create a sample ModelQuantization instance."""
    quant = ModelQuantization()
    quant.id = 1
    quant.model_id = 1
    quant.quantization = "awq"
    quant.file_path = "qwen2.5-72b-instruct-awq"
    quant.file_size_gb = 45.0
    quant.vram_required_gb = 48.0
    quant.gpu_count = 2
    return quant


@pytest.fixture
def sample_config():
    """Create a sample ContainerConfig instance."""
    config = ContainerConfig()
    config.id = 1
    config.model_quant_id = 1
    config.runtime = "vllm"
    config.context_length = 8192
    config.max_parallel = 4
    config.tensor_parallel = 2
    config.pipeline_parallel = 1
    config.extra_args = {}
    return config


class TestPortAllocator:
    """Test cases for PortAllocator."""

    @pytest.mark.asyncio
    async def test_allocate_single_port(self, port_allocator):
        """Test allocating a single port."""
        port = await port_allocator.allocate()
        assert 8001 <= port <= 8999
        assert port in await port_allocator.get_allocated()

    @pytest.mark.asyncio
    async def test_allocate_multiple_ports(self, port_allocator):
        """Test allocating multiple ports returns unique values."""
        ports = set()
        for _ in range(10):
            port = await port_allocator.allocate()
            assert port not in ports, "Port should be unique"
            ports.add(port)

        allocated = await port_allocator.get_allocated()
        assert len(allocated) == 10
        assert ports == allocated

    @pytest.mark.asyncio
    async def test_release_port(self, port_allocator):
        """Test releasing a port makes it available again."""
        port = await port_allocator.allocate()
        assert port in await port_allocator.get_allocated()

        await port_allocator.release(port)
        assert port not in await port_allocator.get_allocated()

    @pytest.mark.asyncio
    async def test_allocate_after_release(self, port_allocator):
        """Test that released port can be reallocated."""
        port1 = await port_allocator.allocate()
        await port_allocator.release(port1)

        port2 = await port_allocator.allocate()
        # Should get the same port back since it's the first available
        assert port2 == 8001

    @pytest.mark.asyncio
    async def test_port_exhaustion(self):
        """Test error when all ports are allocated."""
        # Create allocator with very small range
        allocator = PortAllocator(min_port=8001, max_port=8003)

        # Allocate all ports
        port1 = await allocator.allocate()
        port2 = await allocator.allocate()
        port3 = await allocator.allocate()

        # Next allocation should fail
        with pytest.raises(RuntimeError, match="No available ports"):
            await allocator.allocate()

    @pytest.mark.asyncio
    async def test_thread_safety(self, port_allocator):
        """Test port allocation is thread-safe with concurrent requests."""
        async def allocate_port():
            return await port_allocator.allocate()

        # Allocate 20 ports concurrently
        tasks = [allocate_port() for _ in range(20)]
        ports = await asyncio.gather(*tasks)

        # All ports should be unique
        assert len(ports) == len(set(ports)), "All ports should be unique"
        assert len(await port_allocator.get_allocated()) == 20


class TestContainerCommandGenerator:
    """Test cases for ContainerCommandGenerator."""

    @pytest.mark.asyncio
    async def test_vllm_single_gpu(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test vLLM command generation with single GPU."""
        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        gpus = [0]
        port = 8001

        cmd = await generator.generate(
            sample_config,
            sample_model_quant,
            sample_model,
            gpus,
            port
        )

        # Verify basic command structure
        assert cmd[0:4] == ["podman", "run", "-d", "--rm"]

        # Verify container name
        assert "--name" in cmd
        name_idx = cmd.index("--name")
        assert cmd[name_idx + 1].startswith("vllm-qwen2-5-72b-instruct-awq-")

        # Verify GPU device
        assert "--device" in cmd
        device_idx = cmd.index("--device")
        assert cmd[device_idx + 1] == "nvidia.com/gpu=0"

        # Verify volume mount
        assert "-v" in cmd
        vol_idx = cmd.index("-v")
        assert cmd[vol_idx + 1] == "/test/models:/models:ro"

        # Verify shared memory
        assert "--shm-size" in cmd
        shm_idx = cmd.index("--shm-size")
        assert cmd[shm_idx + 1] == "16g"

        # Verify port mapping
        assert "-p" in cmd
        port_idx = cmd.index("-p")
        assert cmd[port_idx + 1] == "8001:8000"

        # Verify environment variables
        assert "-e" in cmd
        env_indices = [i for i, x in enumerate(cmd) if x == "-e"]
        env_vars = [cmd[i + 1] for i in env_indices]
        assert "CUDA_VISIBLE_DEVICES=0" in env_vars

        # Verify labels
        label_indices = [i for i, x in enumerate(cmd) if x == "--label"]
        labels = [cmd[i + 1] for i in label_indices]
        assert "llm-serve=true" in labels
        assert "model=qwen2.5-72b-instruct-awq" in labels
        assert "runtime=vllm" in labels
        assert "gpus=[0]" in labels

        # Verify vLLM image
        assert "vllm/vllm-openai:latest" in cmd

        # Verify vLLM arguments
        assert "--model" in cmd
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "/models/qwen2.5-72b-instruct-awq"

        assert "--max-model-len" in cmd
        len_idx = cmd.index("--max-model-len")
        assert cmd[len_idx + 1] == "8192"

        assert "--tensor-parallel-size" in cmd
        tp_idx = cmd.index("--tensor-parallel-size")
        assert cmd[tp_idx + 1] == "2"

    @pytest.mark.asyncio
    async def test_vllm_multi_gpu(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test vLLM command generation with multiple GPUs."""
        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        gpus = [0, 1, 2, 3]
        port = 8002

        cmd = await generator.generate(
            sample_config,
            sample_model_quant,
            sample_model,
            gpus,
            port
        )

        # Verify all GPU devices are present
        device_indices = [i for i, x in enumerate(cmd) if x == "--device"]
        assert len(device_indices) == 4

        devices = [cmd[i + 1] for i in device_indices]
        assert "nvidia.com/gpu=0" in devices
        assert "nvidia.com/gpu=1" in devices
        assert "nvidia.com/gpu=2" in devices
        assert "nvidia.com/gpu=3" in devices

        # Verify CUDA_VISIBLE_DEVICES
        env_indices = [i for i, x in enumerate(cmd) if x == "-e"]
        env_vars = [cmd[i + 1] for i in env_indices]
        assert "CUDA_VISIBLE_DEVICES=0,1,2,3" in env_vars

        # Verify GPU label
        label_indices = [i for i, x in enumerate(cmd) if x == "--label"]
        labels = [cmd[i + 1] for i in label_indices]
        # Check that gpus label exists and can be parsed as JSON
        gpu_labels = [l for l in labels if l.startswith("gpus=")]
        assert len(gpu_labels) == 1
        gpu_list = json.loads(gpu_labels[0].split("=", 1)[1])
        assert gpu_list == [0, 1, 2, 3]

    @pytest.mark.asyncio
    async def test_gpu_device_formatting(self):
        """Test GPU device argument formatting."""
        generator = ContainerCommandGenerator(model_path="/test/models")

        # Single GPU
        devices = generator._format_gpu_devices([0])
        assert devices == ["--device", "nvidia.com/gpu=0"]

        # Multiple GPUs
        devices = generator._format_gpu_devices([0, 2, 4])
        assert devices == [
            "--device", "nvidia.com/gpu=0",
            "--device", "nvidia.com/gpu=2",
            "--device", "nvidia.com/gpu=4"
        ]

        # Empty list
        devices = generator._format_gpu_devices([])
        assert devices == []

    @pytest.mark.asyncio
    async def test_env_args_building(self):
        """Test environment variable argument building."""
        generator = ContainerCommandGenerator(model_path="/test/models")

        # No extra env vars
        env_args = generator._build_env_args({}, [0, 1])
        assert env_args == ["-e", "CUDA_VISIBLE_DEVICES=0,1"]

        # With extra env vars
        config_env = {
            "HF_TOKEN": "test_token",
            "CUSTOM_VAR": "value123"
        }
        env_args = generator._build_env_args(config_env, [2])
        assert "-e" in env_args
        assert "CUDA_VISIBLE_DEVICES=2" in env_args
        assert "HF_TOKEN=test_token" in env_args
        assert "CUSTOM_VAR=value123" in env_args

        # CUDA_VISIBLE_DEVICES in config should be ignored
        config_env = {"CUDA_VISIBLE_DEVICES": "should_be_ignored"}
        env_args = generator._build_env_args(config_env, [1, 2])
        cuda_vars = [arg for arg in env_args if "CUDA_VISIBLE_DEVICES" in arg]
        assert len(cuda_vars) == 1
        assert "CUDA_VISIBLE_DEVICES=1,2" in env_args

    @pytest.mark.asyncio
    async def test_label_building(self):
        """Test container label building."""
        generator = ContainerCommandGenerator(model_path="/test/models")

        labels = generator._build_label_args(
            "qwen2.5-7b-fp16",
            "vllm",
            [0, 1]
        )

        # Check all required labels
        assert "--label" in labels
        assert "llm-serve=true" in labels
        assert "model=qwen2.5-7b-fp16" in labels
        assert "runtime=vllm" in labels

        # Check GPU JSON label
        gpu_label = [l for l in labels if l.startswith("gpus=")]
        assert len(gpu_label) == 1
        gpu_list = json.loads(gpu_label[0].split("=", 1)[1])
        assert gpu_list == [0, 1]

    @pytest.mark.asyncio
    async def test_container_name_generation(self):
        """Test container name generation."""
        generator = ContainerCommandGenerator(model_path="/test/models")

        name = generator._container_name("qwen2.5-72b-instruct", "awq")

        # Should have the right format
        assert name.startswith("vllm-qwen2-5-72b-instruct-awq-")

        # Should have random suffix
        parts = name.split("-")
        assert len(parts[-1]) == 8  # UUID hex[:8]

        # Multiple calls should generate different names
        name2 = generator._container_name("qwen2.5-72b-instruct", "awq")
        assert name != name2

    @pytest.mark.asyncio
    async def test_extra_vllm_args(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test adding extra vLLM arguments from config."""
        # Add extra vLLM args to config
        sample_config.extra_args = {
            "vllm_args": ["--trust-remote-code", "--enable-chunked-prefill"]
        }

        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        cmd = await generator.generate(
            sample_config,
            sample_model_quant,
            sample_model,
            [0],
            8001
        )

        # Verify extra args are included
        assert "--trust-remote-code" in cmd
        assert "--enable-chunked-prefill" in cmd

    @pytest.mark.asyncio
    async def test_custom_image(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test using custom container image."""
        # Set custom image in config
        sample_config.extra_args = {
            "image": "custom/vllm:v0.2.0"
        }

        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        cmd = await generator.generate(
            sample_config,
            sample_model_quant,
            sample_model,
            [0],
            8001
        )

        # Verify custom image is used
        assert "custom/vllm:v0.2.0" in cmd
        assert "vllm/vllm-openai:latest" not in cmd

    @pytest.mark.asyncio
    async def test_port_auto_allocation(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test automatic port allocation when port not specified."""
        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        # Don't specify port
        cmd = await generator.generate(
            sample_config,
            sample_model_quant,
            sample_model,
            [0],
            None  # No port specified
        )

        # Port should be automatically allocated
        port_idx = cmd.index("-p")
        port_mapping = cmd[port_idx + 1]
        allocated_port = int(port_mapping.split(":")[0])

        assert 8001 <= allocated_port <= 8999
        assert allocated_port in await port_allocator.get_allocated()

    @pytest.mark.asyncio
    async def test_sglang_not_implemented(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test that SGLang runtime raises NotImplementedError."""
        sample_config.runtime = "sglang"

        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        with pytest.raises(NotImplementedError, match="Runtime sglang not yet implemented"):
            await generator.generate(
                sample_config,
                sample_model_quant,
                sample_model,
                [0],
                8001
            )

    @pytest.mark.asyncio
    async def test_llamacpp_not_implemented(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test that llama.cpp runtime raises NotImplementedError."""
        sample_config.runtime = "llamacpp"

        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        with pytest.raises(NotImplementedError, match="Runtime llamacpp not yet implemented"):
            await generator.generate(
                sample_config,
                sample_model_quant,
                sample_model,
                [0],
                8001
            )

    @pytest.mark.asyncio
    async def test_unknown_runtime(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test that unknown runtime raises ValueError."""
        sample_config.runtime = "unknown_runtime"

        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        with pytest.raises(ValueError, match="Unknown runtime: unknown_runtime"):
            await generator.generate(
                sample_config,
                sample_model_quant,
                sample_model,
                [0],
                8001
            )

    @pytest.mark.asyncio
    async def test_pipeline_parallel(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test pipeline parallel configuration."""
        sample_config.pipeline_parallel = 2

        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        cmd = await generator.generate(
            sample_config,
            sample_model_quant,
            sample_model,
            [0, 1],
            8001
        )

        # Verify pipeline parallel is set
        assert "--pipeline-parallel-size" in cmd
        pp_idx = cmd.index("--pipeline-parallel-size")
        assert cmd[pp_idx + 1] == "2"

    @pytest.mark.asyncio
    async def test_model_without_file_path(
        self,
        port_allocator,
        sample_config,
        sample_model_quant,
        sample_model
    ):
        """Test command generation when model has no file_path."""
        sample_model_quant.file_path = None

        generator = ContainerCommandGenerator(
            port_allocator=port_allocator,
            model_path="/test/models"
        )

        cmd = await generator.generate(
            sample_config,
            sample_model_quant,
            sample_model,
            [0],
            8001
        )

        # Should fall back to model name
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "/models/qwen2.5-72b-instruct"
