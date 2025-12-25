"""
Container command generation service for Phase 7.

This module generates podman run commands for starting LLM inference containers
with various runtimes (vLLM, SGLang, llama.cpp). It handles GPU allocation,
port management, volume mounting, and runtime-specific arguments.
"""

import asyncio
import json
from typing import Optional
from uuid import uuid4

from dashboard.backend.config import settings
from dashboard.backend.models.database import ContainerConfig, Model, ModelQuantization


class PortAllocator:
    """
    Thread-safe port allocator for container services.

    Manages allocation and deallocation of ports in the range 8001-8999
    for container services. Uses asyncio.Lock for thread safety.
    """

    def __init__(self, min_port: int = 8001, max_port: int = 8999):
        """
        Initialize port allocator.

        Args:
            min_port: Minimum port number (inclusive)
            max_port: Maximum port number (inclusive)
        """
        self.min_port = min_port
        self.max_port = max_port
        self._allocated: set[int] = set()
        self._lock = asyncio.Lock()

    async def allocate(self) -> int:
        """
        Allocate next available port.

        Returns:
            Available port number

        Raises:
            RuntimeError: If no ports are available
        """
        async with self._lock:
            for port in range(self.min_port, self.max_port + 1):
                if port not in self._allocated:
                    self._allocated.add(port)
                    return port
            raise RuntimeError(
                f"No available ports in range {self.min_port}-{self.max_port}"
            )

    async def release(self, port: int) -> None:
        """
        Release a previously allocated port.

        Args:
            port: Port number to release
        """
        async with self._lock:
            self._allocated.discard(port)

    async def get_allocated(self) -> set[int]:
        """
        Get set of currently allocated ports.

        Returns:
            Set of allocated port numbers
        """
        async with self._lock:
            return self._allocated.copy()


class ContainerCommandGenerator:
    """
    Generates podman run commands for LLM inference containers.

    Supports multiple runtimes (vLLM, SGLang, llama.cpp) and handles
    GPU allocation, port management, volume mounting, and runtime-specific
    arguments.
    """

    # Default container images for each runtime
    DEFAULT_IMAGES = {
        "vllm": "vllm/vllm-openai:latest",
        "sglang": "lmsysorg/sglang:latest",
        "llamacpp": "ghcr.io/ggerganov/llama.cpp:server",
    }

    def __init__(
        self,
        port_allocator: Optional[PortAllocator] = None,
        model_path: Optional[str] = None
    ):
        """
        Initialize command generator.

        Args:
            port_allocator: Port allocator instance (creates new if None)
            model_path: Path to model storage (uses settings.model_path if None)
        """
        self.port_allocator = port_allocator or PortAllocator()
        self.model_path = model_path or settings.model_path

    async def generate(
        self,
        config: ContainerConfig,
        model_quant: ModelQuantization,
        model: Model,
        gpus: list[int],
        port: Optional[int] = None
    ) -> list[str]:
        """
        Generate podman run command for the specified runtime.

        Args:
            config: Container configuration
            model_quant: Model quantization details
            model: Base model information
            gpus: List of GPU indices to use
            port: Port to use (allocates new if None)

        Returns:
            Command as list of strings (suitable for subprocess)

        Raises:
            ValueError: If runtime is not supported
        """
        runtime = config.runtime.lower()

        if runtime == "vllm":
            return await self._generate_vllm(config, model_quant, model, gpus, port)
        elif runtime == "sglang":
            return await self._generate_sglang(config, model_quant, model, gpus, port)
        elif runtime == "llamacpp":
            return await self._generate_llamacpp(config, model_quant, model, gpus, port)
        else:
            raise ValueError(f"Unknown runtime: {runtime}")

    async def _generate_vllm(
        self,
        config: ContainerConfig,
        model_quant: ModelQuantization,
        model: Model,
        gpus: list[int],
        port: Optional[int] = None
    ) -> list[str]:
        """
        Generate vLLM podman run command.

        Args:
            config: Container configuration
            model_quant: Model quantization details
            model: Base model information
            gpus: List of GPU indices to use
            port: Port to use (allocates new if None)

        Returns:
            Complete podman run command as list of strings
        """
        # Allocate port if not provided
        if port is None:
            port = await self.port_allocator.allocate()

        # Build model identifier for labels
        model_quant_str = f"{model.name}-{model_quant.quantization}"

        # Start building command
        cmd = ["podman", "run", "-d", "--rm"]

        # Add container name
        container_name = self._container_name(model.name, model_quant.quantization)
        cmd.extend(["--name", container_name])

        # Add GPU devices
        cmd.extend(self._format_gpu_devices(gpus))

        # Add volume mount for models (read-only)
        cmd.extend(["-v", f"{self.model_path}:/models:ro"])

        # Add shared memory size
        cmd.extend(["--shm-size", "16g"])

        # Add port mapping
        cmd.extend(["-p", f"{port}:8000"])

        # Add environment variables
        env_dict = config.extra_args or {} if isinstance(config.extra_args, dict) else {}
        cmd.extend(self._build_env_args(env_dict, gpus))

        # Add labels
        cmd.extend(
            self._build_label_args(model_quant_str, config.runtime, gpus)
        )

        # Add container image
        image = self.DEFAULT_IMAGES["vllm"]
        if config.extra_args and isinstance(config.extra_args, dict):
            image = config.extra_args.get("image", image)
        cmd.append(image)

        # Add vLLM arguments
        # Model path (relative to container's /models mount)
        if model_quant.file_path:
            # Use file_path if available
            model_path_in_container = f"/models/{model_quant.file_path}"
        else:
            # Fallback to model name
            model_path_in_container = f"/models/{model.name}"

        cmd.extend(["--model", model_path_in_container])

        # Max model length (context window)
        cmd.extend(["--max-model-len", str(config.context_length)])

        # Tensor parallel size
        if config.tensor_parallel > 1:
            cmd.extend(["--tensor-parallel-size", str(config.tensor_parallel)])

        # Pipeline parallel size (if supported)
        if config.pipeline_parallel > 1:
            cmd.extend(["--pipeline-parallel-size", str(config.pipeline_parallel)])

        # Max parallel requests
        if config.max_parallel:
            # vLLM uses --max-num-seqs for this
            cmd.extend(["--max-num-seqs", str(config.max_parallel)])

        # Add any extra runtime arguments from config
        if config.extra_args and isinstance(config.extra_args, dict):
            extra_vllm_args = config.extra_args.get("vllm_args", [])
            if isinstance(extra_vllm_args, list):
                cmd.extend(extra_vllm_args)

        return cmd

    async def _generate_sglang(
        self,
        config: ContainerConfig,
        model_quant: ModelQuantization,
        model: Model,
        gpus: list[int],
        port: Optional[int] = None
    ) -> list[str]:
        """
        Generate SGLang podman run command.

        Args:
            config: Container configuration
            model_quant: Model quantization details
            model: Base model information
            gpus: List of GPU indices to use
            port: Port to use (allocates new if None)

        Returns:
            Complete podman run command as list of strings

        Raises:
            NotImplementedError: SGLang runtime not yet implemented
        """
        raise NotImplementedError("Runtime sglang not yet implemented")

    async def _generate_llamacpp(
        self,
        config: ContainerConfig,
        model_quant: ModelQuantization,
        model: Model,
        gpus: list[int],
        port: Optional[int] = None
    ) -> list[str]:
        """
        Generate llama.cpp podman run command.

        Args:
            config: Container configuration
            model_quant: Model quantization details
            model: Base model information
            gpus: List of GPU indices to use
            port: Port to use (allocates new if None)

        Returns:
            Complete podman run command as list of strings

        Raises:
            NotImplementedError: llama.cpp runtime not yet implemented
        """
        raise NotImplementedError("Runtime llamacpp not yet implemented")

    def _format_gpu_devices(self, gpus: list[int]) -> list[str]:
        """
        Format GPU device arguments for podman.

        Args:
            gpus: List of GPU indices

        Returns:
            List of device arguments: ["--device", "nvidia.com/gpu=0", ...]
        """
        devices = []
        for gpu_idx in gpus:
            devices.extend(["--device", f"nvidia.com/gpu={gpu_idx}"])
        return devices

    def _build_env_args(self, config_env: dict, gpus: list[int]) -> list[str]:
        """
        Build environment variable arguments for podman.

        Args:
            config_env: Environment variables from config
            gpus: List of GPU indices

        Returns:
            List of environment arguments: ["-e", "KEY=VALUE", ...]
        """
        env_args = []

        # Add CUDA_VISIBLE_DEVICES
        gpu_list = ",".join(str(gpu) for gpu in gpus)
        env_args.extend(["-e", f"CUDA_VISIBLE_DEVICES={gpu_list}"])

        # Add any extra environment variables from config
        for key, value in config_env.items():
            if key != "CUDA_VISIBLE_DEVICES":  # Don't override our GPU setting
                env_args.extend(["-e", f"{key}={value}"])

        return env_args

    def _build_label_args(
        self,
        model_quant: str,
        runtime: str,
        gpus: list[int]
    ) -> list[str]:
        """
        Build label arguments for podman container.

        Args:
            model_quant: Model and quantization identifier
            runtime: Runtime name
            gpus: List of GPU indices

        Returns:
            List of label arguments: ["--label", "key=value", ...]
        """
        labels = []

        # Standard labels
        labels.extend(["--label", "llm-serve=true"])
        labels.extend(["--label", f"model={model_quant}"])
        labels.extend(["--label", f"runtime={runtime}"])

        # GPU list as JSON
        gpu_json = json.dumps(gpus)
        labels.extend(["--label", f"gpus={gpu_json}"])

        return labels

    def _container_name(self, model_name: str, quant: str) -> str:
        """
        Generate unique container name.

        Args:
            model_name: Base model name
            quant: Quantization type

        Returns:
            Container name in format: vllm-{model_name}-{quant}-{random_id}
        """
        # Sanitize model name and quant (remove special characters)
        safe_model = model_name.replace(".", "-").replace("_", "-")
        safe_quant = quant.replace("_", "-").replace(".", "-")

        # Add random suffix for uniqueness
        random_id = uuid4().hex[:8]

        return f"vllm-{safe_model}-{safe_quant}-{random_id}"
