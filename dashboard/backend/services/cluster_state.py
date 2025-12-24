"""Cluster state service - manages in-memory cluster state.

This service maintains real-time cluster state updated from daemon
WebSocket connections and provides methods to query current state.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class GPUState:
    """GPU state information."""
    gpu_index: int
    gpu_uuid: str
    gpu_name: str
    memory_total_gb: float
    memory_used_gb: float
    utilization: int
    temperature_c: int
    assigned_model: Optional[str] = None


@dataclass
class ContainerState:
    """Container state information."""
    container_id: str
    model: str
    runtime: str
    gpus: List[int]
    status: str  # starting, running, ready, failed, stopped
    uptime: Optional[int] = None


@dataclass
class MachineState:
    """Machine state information."""
    machine_id: str
    hostname: str
    connected: bool
    last_seen: datetime
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    cpu_load_percent: Optional[float] = None
    memory_total_gb: Optional[float] = None
    memory_used_gb: Optional[float] = None
    memory_available_gb: Optional[float] = None
    gpus: List[GPUState] = field(default_factory=list)
    containers: List[ContainerState] = field(default_factory=list)


@dataclass
class ClusterStatus:
    """Cluster-wide status summary."""
    total_machines: int = 0
    online_machines: int = 0
    total_gpus: int = 0
    free_gpus: int = 0
    running_models: list[str] = None

    def __post_init__(self):
        if self.running_models is None:
            self.running_models = []


class ClusterStateService:
    """Manages real-time cluster state in memory.

    This service tracks all machines, their stats, and running containers.
    State is updated from daemon WebSocket connections and queries are
    served from memory for fast access.

    Thread-safe for concurrent access from multiple async tasks.
    """

    def __init__(self):
        # Machine states by machine_id
        self._machines: Dict[str, MachineState] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Optional callback for UI updates
        self._ui_update_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None

        logger.info("cluster_state_initialized")

    def set_ui_update_callback(
        self, callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Set callback function for UI update notifications.

        Args:
            callback: Async function to call with (update_type, data)
        """
        self._ui_update_callback = callback

    async def update_machine_stats(
        self, machine_id: str, stats: Dict[str, Any]
    ) -> None:
        """Update machine stats from daemon report.

        Args:
            machine_id: Machine identifier
            stats: Stats dictionary from daemon
        """
        async with self._lock:
            # Get or create machine state
            if machine_id not in self._machines:
                self._machines[machine_id] = MachineState(
                    machine_id=machine_id,
                    hostname=stats.get("hostname", machine_id),
                    connected=True,
                    last_seen=datetime.utcnow(),
                )

            machine = self._machines[machine_id]
            machine.last_seen = datetime.utcnow()
            machine.connected = True

            # Update CPU stats
            cpu_stats = stats.get("cpu", {})
            if cpu_stats:
                machine.cpu_model = cpu_stats.get("model")
                machine.cpu_cores = cpu_stats.get("cores")
                machine.cpu_load_percent = cpu_stats.get("load_percent")

            # Update memory stats
            memory_stats = stats.get("memory", {})
            if memory_stats:
                machine.memory_total_gb = memory_stats.get("total_gb")
                machine.memory_used_gb = memory_stats.get("used_gb")
                machine.memory_available_gb = memory_stats.get("available_gb")

            # Update GPU stats
            gpu_stats = stats.get("gpus", [])
            machine.gpus = []
            for gpu in gpu_stats:
                gpu_state = GPUState(
                    gpu_index=gpu.get("index", 0),
                    gpu_uuid=gpu.get("uuid", ""),
                    gpu_name=gpu.get("name", ""),
                    memory_total_gb=gpu.get("memory_total_gb", 0.0),
                    memory_used_gb=gpu.get("memory_used_gb", 0.0),
                    utilization=gpu.get("utilization", 0),
                    temperature_c=gpu.get("temperature_c", 0),
                    assigned_model=gpu.get("assigned_model"),
                )
                machine.gpus.append(gpu_state)

            # Update container stats
            container_stats = stats.get("containers", [])
            machine.containers = []
            for container in container_stats:
                container_state = ContainerState(
                    container_id=container.get("id", ""),
                    model=container.get("model", ""),
                    runtime=container.get("runtime", ""),
                    gpus=container.get("gpus", []),
                    status=container.get("status", "unknown"),
                    uptime=container.get("uptime"),
                )
                machine.containers.append(container_state)

        # Notify UI if callback is set
        if self._ui_update_callback:
            try:
                await self._ui_update_callback(
                    "stats_updated",
                    {
                        "machine_id": machine_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            except Exception as e:
                logger.error(
                    "ui_update_callback_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    async def get_machine(self, machine_id: str) -> Optional[MachineState]:
        """Get machine state by machine_id.

        Args:
            machine_id: Machine identifier

        Returns:
            MachineState if found, None otherwise
        """
        async with self._lock:
            return self._machines.get(machine_id)

    async def get_all_machines(self) -> Dict[str, MachineState]:
        """Get all machine states.

        Returns:
            Dict mapping machine_id to MachineState
        """
        async with self._lock:
            return self._machines.copy()

    async def mark_machine_online(self, machine_id: str, hostname: str) -> None:
        """Mark a machine as online.

        Args:
            machine_id: Machine identifier
            hostname: Machine hostname
        """
        async with self._lock:
            if machine_id not in self._machines:
                self._machines[machine_id] = MachineState(
                    machine_id=machine_id,
                    hostname=hostname,
                    connected=True,
                    last_seen=datetime.utcnow(),
                )
            else:
                machine = self._machines[machine_id]
                machine.connected = True
                machine.last_seen = datetime.utcnow()

        logger.info("machine_marked_online", machine_id=machine_id)

        # Notify UI
        if self._ui_update_callback:
            try:
                await self._ui_update_callback(
                    "machine_connected",
                    {
                        "machine_id": machine_id,
                        "hostname": hostname,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            except Exception as e:
                logger.error(
                    "ui_update_callback_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    async def mark_machine_offline(self, machine_id: str) -> None:
        """Mark a machine as offline.

        Args:
            machine_id: Machine identifier
        """
        async with self._lock:
            if machine_id in self._machines:
                machine = self._machines[machine_id]
                machine.connected = False

        logger.info("machine_marked_offline", machine_id=machine_id)

        # Notify UI
        if self._ui_update_callback:
            try:
                await self._ui_update_callback(
                    "machine_disconnected",
                    {
                        "machine_id": machine_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            except Exception as e:
                logger.error(
                    "ui_update_callback_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    async def update_container_status(
        self, machine_id: str, container_id: str, status: str
    ) -> None:
        """Update container status for a machine.

        Args:
            machine_id: Machine identifier
            container_id: Container identifier
            status: New status (starting, running, ready, failed, stopped)
        """
        async with self._lock:
            if machine_id not in self._machines:
                logger.warning(
                    "update_container_status_machine_not_found",
                    machine_id=machine_id,
                    container_id=container_id,
                )
                return

            machine = self._machines[machine_id]

            # Find and update container
            for container in machine.containers:
                if container.container_id == container_id:
                    container.status = status
                    logger.info(
                        "container_status_updated",
                        machine_id=machine_id,
                        container_id=container_id,
                        status=status,
                    )
                    break
            else:
                # Container not found, this might be a new container
                logger.debug(
                    "update_container_status_container_not_found",
                    machine_id=machine_id,
                    container_id=container_id,
                )

        # Notify UI
        if self._ui_update_callback:
            try:
                await self._ui_update_callback(
                    "container_status_changed",
                    {
                        "machine_id": machine_id,
                        "container_id": container_id,
                        "status": status,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            except Exception as e:
                logger.error(
                    "ui_update_callback_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    def get_status(self) -> ClusterStatus:
        """Get current cluster status summary.

        Returns:
            ClusterStatus with aggregated cluster metrics
        """
        total_machines = len(self._machines)
        online_machines = sum(1 for m in self._machines.values() if m.connected)
        total_gpus = sum(len(m.gpus) for m in self._machines.values())

        # Count free GPUs (no assigned model)
        free_gpus = sum(
            1
            for m in self._machines.values()
            for gpu in m.gpus
            if gpu.assigned_model is None
        )

        # Get running models
        running_models = list(
            set(
                container.model
                for m in self._machines.values()
                for container in m.containers
                if container.status in ("running", "ready")
            )
        )

        return ClusterStatus(
            total_machines=total_machines,
            online_machines=online_machines,
            total_gpus=total_gpus,
            free_gpus=free_gpus,
            running_models=running_models,
        )


# Singleton instance
cluster_state = ClusterStateService()
