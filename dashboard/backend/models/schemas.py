"""
Pydantic schemas for the LLM Serve Dashboard API.

This module contains all request/response schemas using Pydantic v2 patterns.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Machine Schemas
# ============================================================================

class MachineBase(BaseModel):
    """Base schema for machine with common fields."""
    hostname: str
    ip_address: str
    notes: Optional[str] = None


class MachineCreate(MachineBase):
    """Schema for creating a new machine."""
    pass


class MachineResponse(MachineBase):
    """Full machine response schema."""
    id: str
    first_seen: datetime
    last_seen: datetime
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    status: str  # Computed field: 'online', 'offline', etc.

    model_config = ConfigDict(from_attributes=True)


class MachineListItem(BaseModel):
    """Summary schema for machine list views."""
    id: str
    hostname: str
    ip_address: str
    status: str
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Model Schemas
# ============================================================================

class ModelBase(BaseModel):
    """Base schema for model with common fields."""
    name: str
    provider: str
    huggingface_id: Optional[str] = None
    base_parameters: Optional[str] = None


class ModelCreate(ModelBase):
    """Schema for creating a new model."""
    pass


class QuantizationResponse(BaseModel):
    """Full quantization response schema."""
    id: int
    model_id: int
    quantization: str
    file_path: str
    file_size_gb: Optional[float] = None
    vram_required_gb: Optional[float] = None
    gpu_count: Optional[int] = None
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelResponse(ModelBase):
    """Full model response with nested quantizations."""
    id: int
    added_at: datetime
    quantizations: List[QuantizationResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Quantization Schemas
# ============================================================================

class QuantizationBase(BaseModel):
    """Base schema for quantization with common fields."""
    quantization: str
    file_path: str
    file_size_gb: Optional[float] = None
    vram_required_gb: Optional[float] = None
    gpu_count: Optional[int] = None


class QuantizationCreate(QuantizationBase):
    """Schema for creating a new quantization."""
    model_id: int


# QuantizationResponse is defined above to avoid circular import issues


# ============================================================================
# Container Config Schemas
# ============================================================================

class ContainerConfigBase(BaseModel):
    """Base schema for container config with common fields."""
    runtime: str = Field(default="vllm")
    context_length: Optional[int] = None
    max_parallel: Optional[int] = None
    tensor_parallel: Optional[int] = None
    pipeline_parallel: Optional[int] = None
    extra_args: Optional[Dict[str, Any]] = None


class ContainerConfigCreate(ContainerConfigBase):
    """Schema for creating a new container config."""
    model_quant_id: int


class ModelQuantInfo(BaseModel):
    """Nested model quantization info for container config response."""
    id: int
    model_name: str
    quantization: str
    file_path: str

    model_config = ConfigDict(from_attributes=True)


class ContainerConfigResponse(ContainerConfigBase):
    """Full container config response with nested model_quant info."""
    id: int
    model_quant_id: int
    created_at: datetime
    updated_at: datetime
    model_quant: Optional[ModelQuantInfo] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Stats Schemas
# ============================================================================

class CPUStatsResponse(BaseModel):
    """CPU statistics response schema."""
    time: datetime
    machine_id: int
    cores: int
    load_percent: float

    model_config = ConfigDict(from_attributes=True)


class GPUStatsResponse(BaseModel):
    """GPU statistics response schema."""
    time: datetime
    machine_id: int
    gpu_index: int
    gpu_name: str
    gpu_uuid: str
    temperature_c: Optional[float] = None
    utilization_percent: Optional[float] = None
    memory_total_mb: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_free_mb: Optional[float] = None
    power_draw_w: Optional[float] = None
    power_limit_w: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class MemoryStatsResponse(BaseModel):
    """Memory statistics response schema."""
    time: datetime
    machine_id: int
    total_gb: float
    used_gb: float
    available_gb: float

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Cluster Status Schema
# ============================================================================

class ClusterStatusResponse(BaseModel):
    """Cluster-wide status response schema."""
    total_machines: int
    online_machines: int
    total_gpus: int
    free_gpus: int
    running_models: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Cluster State Schemas (for real-time state tracking)
# ============================================================================

class ContainerState(BaseModel):
    """Container state for real-time tracking.

    Represents a running container on a machine with its current status.
    """
    id: str = Field(description="Container ID")
    model: str = Field(description="Model name being run")
    runtime: str = Field(description="Runtime engine (vllm, sglang, llamacpp)")
    gpus: List[int] = Field(default_factory=list, description="GPU indices assigned to this container")
    status: str = Field(description="Container status (running, starting, stopped, error)")
    uptime: Optional[int] = Field(None, description="Uptime in seconds")

    model_config = ConfigDict(from_attributes=True)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert to dict for API responses."""
        return super().model_dump(**kwargs)


class GPUState(BaseModel):
    """GPU state for real-time tracking.

    Represents current state of a single GPU on a machine.
    """
    index: int = Field(description="GPU index on the machine")
    uuid: str = Field(description="GPU UUID (unique identifier)")
    name: str = Field(description="GPU model name")
    memory_total_mb: float = Field(description="Total GPU memory in MB")
    memory_used_mb: float = Field(description="Used GPU memory in MB")
    memory_free_mb: float = Field(description="Free GPU memory in MB")
    utilization: int = Field(description="GPU utilization percentage (0-100)")
    temperature: Optional[int] = Field(None, description="GPU temperature in Celsius")
    assigned_model: Optional[str] = Field(None, description="Model currently assigned to this GPU")

    model_config = ConfigDict(from_attributes=True)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert to dict for API responses."""
        return super().model_dump(**kwargs)


class MachineState(BaseModel):
    """Machine state for real-time tracking.

    Represents current state of a machine in the cluster with all its resources.
    """
    machine_id: str = Field(description="Unique machine identifier")
    hostname: str = Field(description="Machine hostname")
    connected: bool = Field(description="Whether machine daemon is connected")
    last_seen: datetime = Field(description="Last heartbeat timestamp")
    cpu_cores: int = Field(description="Number of CPU cores")
    cpu_load_percent: float = Field(description="Current CPU load percentage")
    memory_total_gb: float = Field(description="Total system memory in GB")
    memory_used_gb: float = Field(description="Used system memory in GB")
    memory_available_gb: float = Field(description="Available system memory in GB")
    gpus: List[GPUState] = Field(default_factory=list, description="List of GPUs on this machine")
    containers: List[ContainerState] = Field(default_factory=list, description="Running containers on this machine")

    model_config = ConfigDict(from_attributes=True)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert to dict for API responses."""
        return super().model_dump(**kwargs)


class ClusterState(BaseModel):
    """Complete cluster state for real-time tracking.

    Contains the current state of all machines and running models in the cluster.
    This is the top-level state object maintained by the ClusterStateService.
    """
    machines: Dict[str, MachineState] = Field(
        default_factory=dict,
        description="Map of machine_id to MachineState"
    )
    running_models: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Map of model_name to list of machine_ids running it"
    )

    model_config = ConfigDict(from_attributes=True)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert to dict for API responses."""
        return super().model_dump(**kwargs)

    def get_total_machines(self) -> int:
        """Get total number of machines."""
        return len(self.machines)

    def get_online_machines(self) -> int:
        """Get number of connected machines."""
        return sum(1 for m in self.machines.values() if m.connected)

    def get_total_gpus(self) -> int:
        """Get total number of GPUs across all machines."""
        return sum(len(m.gpus) for m in self.machines.values())

    def get_free_gpus(self) -> int:
        """Get number of unassigned GPUs."""
        return sum(
            1 for m in self.machines.values()
            for gpu in m.gpus
            if gpu.assigned_model is None
        )

    def get_running_models_list(self) -> List[str]:
        """Get list of unique running model names."""
        return list(self.running_models.keys())


# ============================================================================
# Settings Schemas
# ============================================================================

class SettingResponse(BaseModel):
    """Setting response schema."""
    key: str
    value: Any
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(BaseModel):
    """Schema for updating a setting."""
    value: Any


# ============================================================================
# Health Schema
# ============================================================================

class HealthResponse(BaseModel):
    """API health check response schema."""
    status: str
    database_connected: bool
    version: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Log Entry Schemas
# ============================================================================

class LogEntry(BaseModel):
    """Individual log entry schema."""
    timestamp: datetime
    level: str
    event: str
    context: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class LogsResponse(BaseModel):
    """Logs response with pagination info."""
    entries: List[LogEntry]
    total_count: int

    model_config = ConfigDict(from_attributes=True)
