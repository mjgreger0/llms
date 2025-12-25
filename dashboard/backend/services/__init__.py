"""Service layer for LLM Serve Dashboard."""

from .cluster_state import (
    cluster_state,
    ClusterStateService,
    ClusterStatus,
    MachineState,
    GPUState,
    ContainerState,
)
from .machine_service import machine_service, MachineService
from .model_service import model_service, ModelService
from .container_service import container_service, ContainerService
from .settings_service import settings_service, SettingsService
from .daemon_manager import daemon_manager, DaemonManager
from .ui_manager import ui_manager, UIManager
from .stats_storage import stats_storage, StatsStorage
from .queue_manager import queue_manager, QueueManager, RequestContext
from .timeout_calculator import (
    ModelSizeTier,
    get_model_size_tier,
    calculate_loading_timeout,
    calculate_inference_timeout,
    extract_param_count_from_name,
    with_timeout,
)
from .model_router import model_router, ModelRouter
from .health_check import health_checker, ContainerHealthChecker
from .container_command import (
    ContainerCommandGenerator,
    PortAllocator,
)

__all__ = [
    # Cluster state
    "cluster_state",
    "ClusterStateService",
    "ClusterStatus",
    "MachineState",
    "GPUState",
    "ContainerState",
    # Machine service
    "machine_service",
    "MachineService",
    # Model service
    "model_service",
    "ModelService",
    # Container service
    "container_service",
    "ContainerService",
    # Settings service
    "settings_service",
    "SettingsService",
    # Daemon manager
    "daemon_manager",
    "DaemonManager",
    # UI manager
    "ui_manager",
    "UIManager",
    # Stats storage
    "stats_storage",
    "StatsStorage",
    # Queue manager
    "queue_manager",
    "QueueManager",
    "RequestContext",
    # Timeout calculator
    "ModelSizeTier",
    "get_model_size_tier",
    "calculate_loading_timeout",
    "calculate_inference_timeout",
    "extract_param_count_from_name",
    "with_timeout",
    # Model router
    "model_router",
    "ModelRouter",
    # Health checker
    "health_checker",
    "ContainerHealthChecker",
    # Container command generator
    "ContainerCommandGenerator",
    "PortAllocator",
]
