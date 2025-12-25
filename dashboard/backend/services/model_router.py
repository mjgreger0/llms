"""Model router - handles routing inference requests to LLM containers."""

import asyncio
from datetime import datetime
from typing import AsyncIterator, Optional, Tuple
import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.backend.services.cluster_state import cluster_state, MachineState, ContainerState
from dashboard.backend.services.daemon_manager import daemon_manager
from dashboard.backend.services.health_check import health_checker
from dashboard.backend.models.database import Model, ModelQuantization, ContainerConfig
from dashboard.backend.db.session import AsyncSessionLocal

logger = structlog.get_logger(__name__)


# Known quantization suffixes
KNOWN_QUANTS = {
    "awq", "gptq", "exl2", "gguf", "bnb",
    "fp16", "fp8", "bf16",
    "q4_k_m", "q8_0", "q5_k_m", "q6_k", "q4_0", "q5_0",
}


class ModelRouter:
    """Routes inference requests to appropriate LLM containers.

    Handles:
    - Model name parsing and quantization resolution
    - Container lookup and endpoint discovery
    - Model loading orchestration
    - Request forwarding with streaming
    - LRU eviction for capacity management
    """

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

        # Track last used time for LRU eviction
        self._last_used: dict[str, datetime] = {}

        logger.info("model_router_initialized")

    async def startup(self):
        """Initialize resources on startup."""
        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))
        logger.info("model_router_started")

    async def shutdown(self):
        """Clean up resources on shutdown."""
        if self._http_client:
            await self._http_client.aclose()
        await health_checker.shutdown()
        logger.info("model_router_shutdown")

    async def ensure_capacity(
        self, model_name: str, quantization: Optional[str]
    ) -> Tuple[str, ContainerState]:
        """Ensure a model is loaded and ready to receive requests.

        This method orchestrates the full process of:
        1. Checking if the model is already running
        2. If not: checking GPU requirements, finding capacity,
           evicting if needed, and loading the model
        3. Health check polling until the container is ready

        Args:
            model_name: Base model name
            quantization: Quantization suffix or None

        Returns:
            Tuple of (machine_id, ContainerState) for the ready container

        Raises:
            ValueError: If model+quant not found in database
            RuntimeError: If no capacity available or loading fails
        """
        async with self._lock:
            # Check if model is already running
            running = await get_running_container(model_name, quantization)

            if running:
                machine_id, container = running
                logger.info(
                    "ensure_capacity_found_running",
                    model=model_name,
                    quantization=quantization,
                    machine_id=machine_id,
                )
                # Update last used time
                model_key = f"{model_name}-{quantization}" if quantization else model_name
                self._last_used[model_key] = datetime.utcnow()
                return running

            # Model not running - need to load it
            logger.info(
                "ensure_capacity_loading_model",
                model=model_name,
                quantization=quantization,
            )

            # Get GPU requirements
            requirements = await get_gpu_requirements(model_name, quantization)

            # Find available machine
            machine_id = await find_available_machine(
                requirements["vram_required_gb"],
                requirements["gpu_count"],
            )

            if not machine_id:
                # Try eviction
                logger.info(
                    "ensure_capacity_evicting",
                    required_vram_gb=requirements["vram_required_gb"],
                )

                await evict_lru_models(requirements["vram_required_gb"])

                # Retry finding machine after eviction
                machine_id = await find_available_machine(
                    requirements["vram_required_gb"],
                    requirements["gpu_count"],
                )

                if not machine_id:
                    raise RuntimeError(
                        "No capacity available even after eviction"
                    )

            # Load model with health check polling
            loading_event = asyncio.Event()

            container = await load_model_with_health_check(
                machine_id=machine_id,
                model_name=model_name,
                quantization=quantization,
                vram_gb=requirements["vram_required_gb"],
                loading_event=loading_event,
            )

            # Update last used time
            model_key = f"{model_name}-{quantization}" if quantization else model_name
            self._last_used[model_key] = datetime.utcnow()

            logger.info(
                "ensure_capacity_complete",
                model=model_name,
                quantization=quantization,
                machine_id=machine_id,
                container_id=container.container_id,
            )

            return (machine_id, container)

    def get_last_used(self, model_key: str) -> Optional[datetime]:
        """Get last used timestamp for a model.

        Args:
            model_key: Model key (e.g., "qwen2.5-72b-instruct-awq")

        Returns:
            Last used datetime or None if never used
        """
        return self._last_used.get(model_key)


def parse_model_name(model_string: str) -> Tuple[str, Optional[str]]:
    """Parse model name to extract base model and quantization.

    Args:
        model_string: Full model name like "qwen2.5-72b-instruct-awq"

    Returns:
        Tuple of (base_model, quantization_or_none)

    Examples:
        "qwen2.5-72b-instruct-awq" -> ("qwen2.5-72b-instruct", "awq")
        "llama3.1-8b-instruct" -> ("llama3.1-8b-instruct", None)
        "mistral-7b-v0.3-q4_k_m" -> ("mistral-7b-v0.3", "q4_k_m")
    """
    # Split on hyphens and underscores
    parts = model_string.replace('_', '-').split('-')

    # Check if last part is a known quantization
    if len(parts) >= 2:
        # Try last part
        last_part = parts[-1].lower()
        if last_part in KNOWN_QUANTS:
            base_model = '-'.join(parts[:-1])
            return (base_model, last_part)

        # Try last two parts (e.g., "q4_k_m" becomes "q4-k-m")
        if len(parts) >= 3:
            last_two = f"{parts[-2]}_{parts[-1]}".lower()
            if last_two in KNOWN_QUANTS:
                base_model = '-'.join(parts[:-2])
                return (base_model, last_two)

    # No quantization found
    return (model_string, None)


async def get_running_container(
    model_name: str, quantization: Optional[str]
) -> Optional[Tuple[str, ContainerState]]:
    """Find a running container for the specified model+quant.

    Args:
        model_name: Base model name
        quantization: Quantization suffix or None

    Returns:
        Tuple of (machine_id, ContainerState) if found and ready, None otherwise
    """
    # Build model+quant identifier
    if quantization:
        model_quant = f"{model_name}-{quantization}"
    else:
        model_quant = model_name

    # Query cluster state for running containers
    machines = await cluster_state.get_all_machines()

    for machine_id, machine in machines.items():
        if not machine.connected:
            continue

        for container in machine.containers:
            # Check if container matches model+quant and is ready
            if container.model == model_quant and container.status == "ready":
                logger.info(
                    "found_running_container",
                    model=model_quant,
                    machine_id=machine_id,
                    container_id=container.container_id,
                )
                return (machine_id, container)

    logger.debug(
        "no_running_container_found",
        model=model_quant,
    )
    return None


async def get_gpu_requirements(
    model_name: str, quantization: Optional[str]
) -> dict:
    """Get GPU requirements for a model+quant from database.

    Returns:
        Dict with keys: vram_required_gb, gpu_count, tensor_parallel, pipeline_parallel, multi_machine

    Raises:
        ValueError: If model+quant not found in database
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized")

    async with AsyncSessionLocal() as db:
        # Query for model and quantization
        stmt = (
            select(ModelQuantization, ContainerConfig)
            .join(Model, Model.id == ModelQuantization.model_id)
            .join(ContainerConfig, ContainerConfig.model_quant_id == ModelQuantization.id)
            .where(Model.name == model_name)
        )

        if quantization:
            stmt = stmt.where(ModelQuantization.quantization == quantization)

        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise ValueError(
                f"Model+quant not found in database: {model_name}"
                + (f"-{quantization}" if quantization else "")
            )

        model_quant, container_config = row

        # Calculate requirements
        vram_required = model_quant.vram_required_gb or 0.0
        gpu_count = model_quant.gpu_count or 1
        tensor_parallel = container_config.tensor_parallel or 1
        pipeline_parallel = container_config.pipeline_parallel or 1

        # Multi-machine if requires more than 8 GPUs (common single-machine limit)
        multi_machine = gpu_count > 8

        requirements = {
            "vram_required_gb": vram_required,
            "gpu_count": gpu_count,
            "tensor_parallel": tensor_parallel,
            "pipeline_parallel": pipeline_parallel,
            "multi_machine": multi_machine,
        }

        logger.info(
            "gpu_requirements_retrieved",
            model=model_name,
            quantization=quantization,
            requirements=requirements,
        )

        return requirements


async def find_available_machine(
    required_vram_gb: float, required_gpu_count: int
) -> Optional[str]:
    """Find a machine with sufficient GPU capacity.

    Args:
        required_vram_gb: Total VRAM needed
        required_gpu_count: Number of GPUs needed

    Returns:
        machine_id if found, None otherwise
    """
    machines = await cluster_state.get_all_machines()

    candidates = []

    for machine_id, machine in machines.items():
        if not machine.connected:
            continue

        # Calculate free VRAM and free GPU count
        free_gpus = []
        total_free_vram = 0.0

        for gpu in machine.gpus:
            if gpu.assigned_model is None:
                free_gpus.append(gpu)
                free_vram = gpu.memory_total_gb - gpu.memory_used_gb
                total_free_vram += free_vram

        # Check if machine has enough capacity
        if len(free_gpus) >= required_gpu_count and total_free_vram >= required_vram_gb:
            # Calculate utilization for tiebreaker
            total_util = sum(gpu.utilization for gpu in machine.gpus)
            avg_util = total_util / len(machine.gpus) if machine.gpus else 0

            candidates.append({
                "machine_id": machine_id,
                "free_gpu_count": len(free_gpus),
                "free_vram_gb": total_free_vram,
                "avg_utilization": avg_util,
            })

    if not candidates:
        logger.warning(
            "no_available_machine",
            required_vram_gb=required_vram_gb,
            required_gpu_count=required_gpu_count,
        )
        return None

    # Sort by: exact GPU count match (prefer), then lowest utilization
    candidates.sort(
        key=lambda c: (
            abs(c["free_gpu_count"] - required_gpu_count),  # Prefer exact match
            c["avg_utilization"],  # Then prefer lower utilization
        )
    )

    best = candidates[0]
    logger.info(
        "found_available_machine",
        machine_id=best["machine_id"],
        free_gpu_count=best["free_gpu_count"],
        free_vram_gb=best["free_vram_gb"],
        avg_utilization=best["avg_utilization"],
    )

    return best["machine_id"]


async def evict_lru_models(
    required_vram_gb: float, target_machine: Optional[str] = None
) -> list[str]:
    """Evict idle models using LRU policy to free capacity.

    Args:
        required_vram_gb: VRAM needed to free
        target_machine: If set, only evict from this machine

    Returns:
        List of evicted model+quant names

    Raises:
        RuntimeError: If cannot free enough capacity
    """
    # Get all machines
    machines = await cluster_state.get_all_machines()

    # Build list of eviction candidates (idle containers)
    candidates = []

    for machine_id, machine in machines.items():
        if target_machine and machine_id != target_machine:
            continue

        if not machine.connected:
            continue

        for container in machine.containers:
            if container.status != "ready":
                continue

            # Check if idle (using last_used tracking)
            # For now, consider all containers as potential candidates
            # In a full implementation, would check queue_manager.is_idle()

            # Calculate VRAM used by this container
            vram_used = 0.0
            for gpu_idx in container.gpus:
                if gpu_idx < len(machine.gpus):
                    gpu = machine.gpus[gpu_idx]
                    vram_used += gpu.memory_used_gb

            candidates.append({
                "machine_id": machine_id,
                "container_id": container.container_id,
                "model": container.model,
                "vram_gb": vram_used,
                "last_used": datetime.utcnow(),  # Placeholder
            })

    if not candidates:
        raise RuntimeError(
            f"Cannot evict models: no idle containers found "
            f"(need {required_vram_gb:.1f}GB)"
        )

    # Sort by last_used (oldest first - LRU)
    candidates.sort(key=lambda c: c["last_used"])

    # Evict greedily until enough VRAM freed
    freed_vram = 0.0
    evicted = []

    for candidate in candidates:
        if freed_vram >= required_vram_gb:
            break

        machine_id = candidate["machine_id"]
        container_id = candidate["container_id"]
        model = candidate["model"]

        try:
            # Send container.stop command to daemon
            await daemon_manager.send_request(
                machine_id=machine_id,
                method="container.stop",
                params={"container_id": container_id},
                timeout=30.0,
            )

            freed_vram += candidate["vram_gb"]
            evicted.append(model)

            logger.info(
                "evicted_model",
                machine_id=machine_id,
                container_id=container_id,
                model=model,
                vram_freed_gb=candidate["vram_gb"],
            )

        except Exception as e:
            logger.error(
                "eviction_failed",
                machine_id=machine_id,
                container_id=container_id,
                model=model,
                error=str(e),
                error_type=type(e).__name__,
            )

    if freed_vram < required_vram_gb:
        raise RuntimeError(
            f"Cannot free enough VRAM: needed {required_vram_gb:.1f}GB, "
            f"freed {freed_vram:.1f}GB"
        )

    logger.info(
        "eviction_complete",
        evicted_models=evicted,
        vram_freed_gb=freed_vram,
    )

    return evicted


async def load_model(
    machine_id: str, model_name: str, quantization: Optional[str],
    loading_event: asyncio.Event
) -> ContainerState:
    """Load a model on a machine.

    Args:
        machine_id: Target machine
        model_name: Model to load
        quantization: Quantization to use
        loading_event: Event to set when loading completes

    Returns:
        ContainerState for the loaded container

    Raises:
        RuntimeError: If loading fails
    """
    # Build model+quant identifier
    if quantization:
        model_quant = f"{model_name}-{quantization}"
    else:
        model_quant = model_name

    logger.info(
        "loading_model",
        machine_id=machine_id,
        model=model_quant,
    )

    # Get container config from database
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized")

    async with AsyncSessionLocal() as db:
        stmt = (
            select(ModelQuantization, ContainerConfig)
            .join(Model, Model.id == ModelQuantization.model_id)
            .join(ContainerConfig, ContainerConfig.model_quant_id == ModelQuantization.id)
            .where(Model.name == model_name)
        )

        if quantization:
            stmt = stmt.where(ModelQuantization.quantization == quantization)

        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise RuntimeError(
                f"Model+quant not found in database: {model_name}"
                + (f"-{quantization}" if quantization else "")
            )

        model_quant_obj, container_config = row

        # Build container.start parameters
        params = {
            "model": model_quant,
            "model_path": model_quant_obj.file_path,
            "runtime": container_config.runtime,
            "gpu_count": model_quant_obj.gpu_count,
            "context_length": container_config.context_length,
            "max_parallel": container_config.max_parallel,
            "tensor_parallel": container_config.tensor_parallel,
            "pipeline_parallel": container_config.pipeline_parallel,
        }

        if container_config.extra_args:
            params["extra_args"] = container_config.extra_args

    try:
        # Send container.start command to daemon
        result = await daemon_manager.send_request(
            machine_id=machine_id,
            method="container.start",
            params=params,
            timeout=300.0,  # 5 minute timeout for loading
        )

        container_id = result.get("container_id")
        if not container_id:
            raise RuntimeError("Daemon did not return container_id")

        logger.info(
            "container_start_initiated",
            machine_id=machine_id,
            container_id=container_id,
            model=model_quant,
        )

        # Poll for container to become ready
        # In a real implementation, this would poll the container's health endpoint
        # For now, we'll wait for cluster state to update
        max_wait = 240  # 4 minutes
        poll_interval = 2  # 2 seconds
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            # Check cluster state for container
            machine = await cluster_state.get_machine(machine_id)
            if machine:
                for container in machine.containers:
                    if container.container_id == container_id:
                        if container.status == "ready":
                            loading_event.set()
                            logger.info(
                                "model_loaded",
                                machine_id=machine_id,
                                container_id=container_id,
                                model=model_quant,
                                elapsed_seconds=elapsed,
                            )
                            return container
                        elif container.status == "failed":
                            raise RuntimeError(
                                f"Container failed to start: {container_id}"
                            )

        raise RuntimeError(
            f"Timeout waiting for container to become ready: {container_id}"
        )

    except Exception as e:
        logger.error(
            "model_loading_failed",
            machine_id=machine_id,
            model=model_quant,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise RuntimeError(f"Failed to load model: {str(e)}") from e


async def load_model_with_health_check(
    machine_id: str,
    model_name: str,
    quantization: Optional[str],
    vram_gb: float,
    loading_event: asyncio.Event
) -> ContainerState:
    """Load a model on a machine with proper health check polling.

    This is an enhanced version of load_model that uses the ContainerHealthChecker
    to poll the container's health endpoint instead of relying on cluster state updates.

    Args:
        machine_id: Target machine
        model_name: Model to load
        quantization: Quantization to use
        vram_gb: VRAM required (for timeout calculation)
        loading_event: Event to set when loading completes

    Returns:
        ContainerState for the loaded container

    Raises:
        RuntimeError: If loading fails
        TimeoutError: If health check times out
    """
    # Build model+quant identifier
    if quantization:
        model_quant = f"{model_name}-{quantization}"
    else:
        model_quant = model_name

    logger.info(
        "loading_model_with_health_check",
        machine_id=machine_id,
        model=model_quant,
        vram_gb=vram_gb,
    )

    # Get container config from database
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized")

    async with AsyncSessionLocal() as db:
        stmt = (
            select(ModelQuantization, ContainerConfig, Model)
            .join(Model, Model.id == ModelQuantization.model_id)
            .join(ContainerConfig, ContainerConfig.model_quant_id == ModelQuantization.id)
            .where(Model.name == model_name)
        )

        if quantization:
            stmt = stmt.where(ModelQuantization.quantization == quantization)

        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise RuntimeError(
                f"Model+quant not found in database: {model_name}"
                + (f"-{quantization}" if quantization else "")
            )

        model_quant_obj, container_config, model_obj = row

        # Build container.start parameters
        params = {
            "model": model_quant,
            "model_path": model_quant_obj.file_path,
            "runtime": container_config.runtime,
            "gpu_count": model_quant_obj.gpu_count,
            "context_length": container_config.context_length,
            "max_parallel": container_config.max_parallel,
            "tensor_parallel": container_config.tensor_parallel,
            "pipeline_parallel": container_config.pipeline_parallel,
        }

        if container_config.extra_args:
            params["extra_args"] = container_config.extra_args

        if container_config.environment:
            params["environment"] = container_config.environment

    try:
        # Send container.start command to daemon
        result = await daemon_manager.send_request(
            machine_id=machine_id,
            method="container.start",
            params=params,
            timeout=300.0,  # 5 minute timeout for starting
        )

        container_id = result.get("container_id")
        container_port = result.get("port", 8000)

        if not container_id:
            raise RuntimeError("Daemon did not return container_id")

        logger.info(
            "container_start_initiated",
            machine_id=machine_id,
            container_id=container_id,
            port=container_port,
            model=model_quant,
        )

        # Get machine info to build health check URL
        machine = await cluster_state.get_machine(machine_id)
        if not machine:
            raise RuntimeError(f"Machine not found: {machine_id}")

        # Build health check endpoint URL
        health_endpoint = f"http://{machine.hostname}:{container_port}"

        # Calculate timeout based on VRAM (larger models take longer)
        timeout = health_checker.calculate_timeout_for_vram(vram_gb)

        logger.info(
            "starting_health_check_polling",
            machine_id=machine_id,
            container_id=container_id,
            endpoint=health_endpoint,
            timeout=timeout,
        )

        # Ensure health checker is started
        await health_checker.startup()

        try:
            # Poll until ready
            await health_checker.poll_until_ready(
                endpoint=health_endpoint,
                timeout=timeout,
                interval=2.0,
            )
        except TimeoutError as e:
            logger.error(
                "health_check_timeout",
                machine_id=machine_id,
                container_id=container_id,
                model=model_quant,
                timeout=timeout,
            )
            raise RuntimeError(
                f"Container health check timed out after {timeout}s: {container_id}"
            ) from e

        # Health check succeeded - set loading event
        loading_event.set()

        # Get container state from cluster
        machine = await cluster_state.get_machine(machine_id)
        if machine:
            for container in machine.containers:
                if container.container_id == container_id:
                    logger.info(
                        "model_loaded_with_health_check",
                        machine_id=machine_id,
                        container_id=container_id,
                        model=model_quant,
                    )
                    return container

        # Container not in cluster state yet, create a minimal ContainerState
        from dashboard.backend.models.schemas import ContainerState as ContainerStateSchema
        container_state = ContainerStateSchema(
            id=container_id,
            model=model_quant,
            runtime=container_config.runtime,
            gpus=[],  # Will be populated by cluster state update
            status="ready",
        )

        logger.info(
            "model_loaded_with_health_check",
            machine_id=machine_id,
            container_id=container_id,
            model=model_quant,
        )

        return container_state

    except Exception as e:
        logger.error(
            "model_loading_with_health_check_failed",
            machine_id=machine_id,
            model=model_quant,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise RuntimeError(f"Failed to load model: {str(e)}") from e


async def forward_request(
    http_client: httpx.AsyncClient,
    container_url: str,
    request_data: dict
) -> AsyncIterator[str]:
    """Forward inference request to container and stream response.

    Args:
        http_client: httpx AsyncClient instance
        container_url: Container's inference endpoint URL
        request_data: OpenAI-format request body

    Yields:
        SSE-formatted response chunks
    """
    logger.debug(
        "forwarding_request",
        container_url=container_url,
        model=request_data.get("model"),
    )

    try:
        async with http_client.stream(
            "POST",
            container_url,
            json=request_data,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line:
                    # Forward SSE-formatted chunks
                    yield f"{line}\n"

        logger.debug(
            "request_forwarding_complete",
            container_url=container_url,
        )

    except httpx.HTTPError as e:
        logger.error(
            "request_forwarding_failed",
            container_url=container_url,
            error=str(e),
            error_type=type(e).__name__,
        )
        # Yield error in SSE format
        error_data = {
            "error": {
                "message": f"Container error: {str(e)}",
                "type": "container_error",
                "code": "container_error",
            }
        }
        import json
        yield f"data: {json.dumps(error_data)}\n\n"


async def route_request(
    router: ModelRouter,
    request: dict,
    request_id: str
) -> AsyncIterator[str]:
    """Route an inference request to appropriate container.

    Full flow:
    1. Parse model name, resolve quantization
    2. Check if model is already running
    3. If not: check capacity, evict if needed, load model
    4. Forward request and stream response

    Args:
        router: ModelRouter instance
        request: OpenAI-format request dict
        request_id: Unique request ID for logging

    Yields:
        SSE-formatted response chunks (including keepalive during loading)
    """
    model_string = request.get("model", "")

    logger.info(
        "routing_request",
        request_id=request_id,
        model=model_string,
    )

    try:
        # Task 3.2: Parse model name
        model_name, quantization = parse_model_name(model_string)

        logger.debug(
            "parsed_model_name",
            request_id=request_id,
            model_name=model_name,
            quantization=quantization,
        )

        # Task 3.3: Check if model is already running
        running = await get_running_container(model_name, quantization)

        if running:
            machine_id, container = running

            # Get machine to build container URL
            machine = await cluster_state.get_machine(machine_id)
            if not machine:
                raise RuntimeError(f"Machine not found: {machine_id}")

            # Build container endpoint URL
            # In a real implementation, would get this from container metadata
            container_url = f"http://{machine.hostname}:8000/v1/chat/completions"

            logger.info(
                "forwarding_to_running_container",
                request_id=request_id,
                machine_id=machine_id,
                container_id=container.container_id,
            )

            # Forward request directly
            async for chunk in forward_request(router._http_client, container_url, request):
                yield chunk

            # Update last_used time
            model_key = f"{model_name}-{quantization}" if quantization else model_name
            router._last_used[model_key] = datetime.utcnow()

        else:
            # Model not running - need to load it
            logger.info(
                "model_not_running_loading",
                request_id=request_id,
                model=model_string,
            )

            # Task 3.4: Get GPU requirements
            requirements = await get_gpu_requirements(model_name, quantization)

            # Task 3.5: Find available machine
            machine_id = await find_available_machine(
                requirements["vram_required_gb"],
                requirements["gpu_count"],
            )

            if not machine_id:
                # Task 3.6: Try eviction if no capacity
                logger.info(
                    "no_capacity_attempting_eviction",
                    request_id=request_id,
                    required_vram_gb=requirements["vram_required_gb"],
                )

                await evict_lru_models(requirements["vram_required_gb"])

                # Retry finding machine after eviction
                machine_id = await find_available_machine(
                    requirements["vram_required_gb"],
                    requirements["gpu_count"],
                )

                if not machine_id:
                    raise RuntimeError(
                        "No capacity available even after eviction"
                    )

            # Task 3.7: Load model
            loading_event = asyncio.Event()

            # Start loading in background
            load_task = asyncio.create_task(
                load_model(machine_id, model_name, quantization, loading_event)
            )

            # Yield keepalive messages during loading
            estimated_wait = 120  # 2 minutes default
            if requirements["vram_required_gb"] > 70:
                estimated_wait = 240
            elif requirements["vram_required_gb"] > 30:
                estimated_wait = 180
            elif requirements["vram_required_gb"] > 10:
                estimated_wait = 120
            else:
                estimated_wait = 90

            start_time = datetime.utcnow()
            while not loading_event.is_set():
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                remaining = max(0, estimated_wait - int(elapsed))

                keepalive_msg = f": loading {model_string}, ~{remaining}s remaining\n\n"
                yield keepalive_msg

                try:
                    await asyncio.wait_for(
                        loading_event.wait(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    pass

            # Wait for load task to complete
            container = await load_task

            # Get machine to build container URL
            machine = await cluster_state.get_machine(machine_id)
            if not machine:
                raise RuntimeError(f"Machine not found: {machine_id}")

            # Build container endpoint URL
            container_url = f"http://{machine.hostname}:8000/v1/chat/completions"

            logger.info(
                "model_loaded_forwarding_request",
                request_id=request_id,
                machine_id=machine_id,
                container_id=container.container_id,
            )

            # Task 3.8: Forward request
            async for chunk in forward_request(router._http_client, container_url, request):
                yield chunk

            # Update last_used time
            model_key = f"{model_name}-{quantization}" if quantization else model_name
            router._last_used[model_key] = datetime.utcnow()

        logger.info(
            "request_routing_complete",
            request_id=request_id,
        )

    except Exception as e:
        logger.error(
            "request_routing_failed",
            request_id=request_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        # Yield error in SSE format
        import json
        error_data = {
            "error": {
                "message": str(e),
                "type": type(e).__name__,
                "code": "routing_error",
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"


# Singleton instance
model_router = ModelRouter()
