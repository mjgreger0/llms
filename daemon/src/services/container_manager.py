"""Container Manager Service - Manages LLM container lifecycle with Podman."""

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from podman import PodmanClient
from podman.domain.containers import Container
from podman.errors import APIError, NotFound

from src.config import config
from src.logger import logger
from src.models import ContainerConfig, ContainerStats


class ContainerManager:
    """
    Manages container lifecycle operations for LLM serving containers.

    This service handles:
    - Starting containers with proper GPU, volume, and environment configuration
    - Stopping and cleaning up containers
    - Querying container status and port mappings
    - Collecting statistics from running containers

    Uses Podman API via unix socket for container management.
    """

    def __init__(self) -> None:
        """Initialize the ContainerManager with PodmanClient."""
        # Build unix socket URI from config path
        socket_uri = f"unix://{config.PODMAN_SOCKET}"

        try:
            self.client = PodmanClient(base_url=socket_uri)
            logger.info(
                "ContainerManager initialized",
                socket=str(config.PODMAN_SOCKET),
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Podman client",
                socket=str(config.PODMAN_SOCKET),
                error=str(e),
            )
            raise

        # Track running containers by model_quant identifier
        self.running_containers: dict[str, Container] = {}

    def _build_gpu_devices(self, gpu_indices: list[int]) -> list[str]:
        """
        Build GPU device specifications for container runtime.

        Args:
            gpu_indices: List of GPU indices to assign to container

        Returns:
            List of device specifications in nvidia.com/gpu=N format
        """
        return [f"nvidia.com/gpu={idx}" for idx in gpu_indices]

    def _build_env(self, config: ContainerConfig) -> dict[str, str]:
        """
        Build environment variables for container.

        Args:
            config: Container configuration

        Returns:
            Dictionary of environment variables
        """
        env = {}

        # Set CUDA_VISIBLE_DEVICES to GPU indices
        if config.gpus:
            env["CUDA_VISIBLE_DEVICES"] = ",".join(str(idx) for idx in config.gpus)

        # vLLM-specific environment variables
        if config.runtime == "vllm":
            env["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

        return env

    def _build_command(self, config: ContainerConfig) -> list[str]:
        """
        Build command arguments for container runtime.

        Args:
            config: Container configuration

        Returns:
            List of command arguments

        Raises:
            ValueError: If runtime is not supported
        """
        # Prefix model path with container mount point
        model_path = f"/models/{Path(config.model_path).name}"

        if config.runtime == "vllm":
            command = [
                "--model", model_path,
                "--max-model-len", str(config.context_length),
                "--tensor-parallel-size", str(config.tensor_parallel),
                "--pipeline-parallel-size", str(config.pipeline_parallel),
                "--max-num-seqs", str(config.max_parallel),
                "--host", "0.0.0.0",
                "--port", "8000",
            ]
        elif config.runtime == "sglang":
            command = [
                "--model-path", model_path,
                "--context-length", str(config.context_length),
                "--tp", str(config.tensor_parallel),
                "--host", "0.0.0.0",
                "--port", "8000",
            ]
        else:
            raise ValueError(f"Unsupported runtime: {config.runtime}")

        return command

    async def start_container(self, config: ContainerConfig) -> str:
        """
        Start a new LLM serving container.

        Args:
            config: Container configuration

        Returns:
            Container ID

        Raises:
            APIError: If container creation fails
            ValueError: If configuration is invalid
        """
        # Generate unique container name
        random_hex = secrets.token_hex(4)
        container_name = f"llm-{config.model_quant}-{random_hex}"

        try:
            # Build configuration components
            environment = self._build_env(config)
            command = self._build_command(config)
            devices = self._build_gpu_devices(config.gpus)

            # Resolve absolute model path on host
            model_host_path = config.model_path
            if not Path(model_host_path).is_absolute():
                model_host_path = str(config.MODEL_PATH / config.model_path)

            # Build container labels for tracking
            labels = {
                "llm-serve": "true",
                "model": config.model_quant,
                "runtime": config.runtime,
                "gpus": json.dumps(config.gpus),
            }

            logger.info(
                "Starting container",
                name=container_name,
                model=config.model_quant,
                runtime=config.runtime,
                gpus=config.gpus,
                image=config.image,
            )

            # Create and start container
            container = self.client.containers.run(
                image=config.image,
                name=container_name,
                detach=True,
                remove=False,
                ports={"8000/tcp": None},  # Dynamic port allocation
                environment=environment,
                command=command,
                devices=devices,
                volumes={
                    model_host_path: {
                        "bind": "/models",
                        "mode": "ro",
                    }
                },
                labels=labels,
                shm_size="16g",
            )

            # Store container reference
            self.running_containers[config.model_quant] = container

            logger.info(
                "Container started successfully",
                container_id=container.id[:12],
                name=container_name,
                model=config.model_quant,
            )

            return container.id

        except APIError as e:
            logger.error(
                "Failed to start container",
                model=config.model_quant,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error starting container",
                model=config.model_quant,
                error=str(e),
            )
            raise

    async def stop_container(self, model_quant: str, evicting: bool = False) -> None:
        """
        Stop and remove a running container.

        Args:
            model_quant: Model quantization identifier
            evicting: Whether this is part of eviction (for logging context)

        Raises:
            ValueError: If container is not found
            APIError: If container stop/remove fails
        """
        # Check if container exists in our tracking
        if model_quant not in self.running_containers:
            logger.warning(
                "Container not found in running containers",
                model=model_quant,
            )
            raise ValueError(f"Container for model {model_quant} not found")

        container = self.running_containers[model_quant]

        try:
            logger.info(
                "Stopping container",
                container_id=container.id[:12],
                model=model_quant,
                evicting=evicting,
            )

            # Stop container with timeout
            container.stop(timeout=30)

            # Remove container
            container.remove()

            # Remove from tracking
            del self.running_containers[model_quant]

            logger.info(
                "Container stopped and removed",
                container_id=container.id[:12],
                model=model_quant,
            )

        except NotFound:
            logger.warning(
                "Container already removed",
                container_id=container.id[:12],
                model=model_quant,
            )
            # Clean up tracking even if container is gone
            del self.running_containers[model_quant]

        except APIError as e:
            logger.error(
                "Failed to stop container",
                container_id=container.id[:12],
                model=model_quant,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error stopping container",
                container_id=container.id[:12],
                model=model_quant,
                error=str(e),
            )
            raise

    def get_container_port(self, model_quant: str) -> Optional[int]:
        """
        Get the host port for a running container.

        Args:
            model_quant: Model quantization identifier

        Returns:
            Host port number, or None if container not found or port not mapped
        """
        if model_quant not in self.running_containers:
            logger.warning(
                "Container not found when looking up port",
                model=model_quant,
            )
            return None

        container = self.running_containers[model_quant]

        try:
            # Reload container data to get current port mappings
            container.reload()

            # Extract port from container.ports mapping
            port_mappings = container.ports.get("8000/tcp")
            if not port_mappings or len(port_mappings) == 0:
                logger.warning(
                    "No port mapping found for container",
                    container_id=container.id[:12],
                    model=model_quant,
                )
                return None

            # Get HostPort from first mapping
            host_port = port_mappings[0].get("HostPort")
            if host_port is None:
                logger.warning(
                    "HostPort not found in mapping",
                    container_id=container.id[:12],
                    model=model_quant,
                )
                return None

            return int(host_port)

        except Exception as e:
            logger.error(
                "Error retrieving container port",
                container_id=container.id[:12],
                model=model_quant,
                error=str(e),
            )
            return None

    def get_running_containers(self) -> list[ContainerStats]:
        """
        Get statistics for all running LLM containers.

        Returns:
            List of ContainerStats for each running LLM container
        """
        container_stats = []

        try:
            # List all containers (running and stopped)
            all_containers = self.client.containers.list(all=True)

            # Filter for containers with llm-serve label
            for container in all_containers:
                labels = container.labels or {}
                if labels.get("llm-serve") != "true":
                    continue

                try:
                    # Parse labels
                    model = labels.get("model", "unknown")
                    runtime = labels.get("runtime", "unknown")
                    gpus_str = labels.get("gpus", "[]")

                    # Decode GPU list from JSON
                    try:
                        gpus = json.loads(gpus_str)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Failed to decode gpus label",
                            container_id=container.id[:12],
                            gpus_str=gpus_str,
                        )
                        gpus = []

                    # Get container status
                    status = container.status

                    # Calculate uptime
                    uptime_seconds = 0
                    if hasattr(container, 'attrs') and container.attrs:
                        state = container.attrs.get("State", {})
                        started_at_str = state.get("StartedAt")
                        if started_at_str:
                            try:
                                # Parse ISO timestamp
                                started_at = datetime.fromisoformat(
                                    started_at_str.replace("Z", "+00:00")
                                )
                                uptime_seconds = int(
                                    (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                                )
                            except Exception as e:
                                logger.debug(
                                    "Failed to parse container start time",
                                    container_id=container.id[:12],
                                    error=str(e),
                                )

                    # Build ContainerStats
                    stats = ContainerStats(
                        id=container.id[:12],
                        model=model,
                        runtime=runtime,
                        gpus=gpus,
                        status=status,
                        uptime_seconds=uptime_seconds,
                    )

                    container_stats.append(stats)

                except Exception as e:
                    logger.error(
                        "Error processing container",
                        container_id=container.id[:12] if hasattr(container, 'id') else "unknown",
                        error=str(e),
                    )
                    continue

        except APIError as e:
            logger.error(
                "Failed to list containers",
                error=str(e),
            )
        except Exception as e:
            logger.error(
                "Unexpected error getting container stats",
                error=str(e),
            )

        return container_stats
