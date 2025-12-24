"""Data models for system and container statistics."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CPUStats(BaseModel):
    """CPU statistics model."""

    manufacturer: str = Field(..., description="CPU manufacturer name")
    model: str = Field(..., description="CPU model name")
    cores: int = Field(..., description="Number of physical CPU cores", ge=1)
    threads: int = Field(..., description="Number of logical CPU threads", ge=1)
    load_percent: float = Field(..., description="Current CPU load percentage", ge=0.0, le=100.0)


class MemoryStats(BaseModel):
    """Memory statistics model."""

    total_gb: float = Field(..., description="Total system memory in GB", ge=0.0)
    used_gb: float = Field(..., description="Used memory in GB", ge=0.0)
    available_gb: float = Field(..., description="Available memory in GB", ge=0.0)


class NetworkInterfaceStats(BaseModel):
    """Network interface statistics model."""

    interface: str = Field(..., description="Network interface name")
    mac_address: str = Field(..., description="MAC address of the interface")
    ip_addresses: list[str] = Field(default_factory=list, description="List of IP addresses")
    speed_mbps: int = Field(..., description="Interface speed in Mbps", ge=0)
    mtu: int = Field(..., description="Maximum transmission unit", ge=0)
    is_up: bool = Field(..., description="Whether the interface is up")
    bytes_sent: int = Field(..., description="Total bytes sent", ge=0)
    bytes_recv: int = Field(..., description="Total bytes received", ge=0)
    bytes_sent_rate: float = Field(..., description="Bytes sent rate (bytes/sec)", ge=0.0)
    bytes_recv_rate: float = Field(..., description="Bytes received rate (bytes/sec)", ge=0.0)


class GPUStats(BaseModel):
    """GPU statistics model."""

    index: int = Field(..., description="GPU index number", ge=0)
    uuid: str = Field(..., description="GPU UUID")
    chip_manufacturer: str = Field(..., description="GPU chip manufacturer")
    chip_model: str = Field(..., description="GPU chip model")
    card_manufacturer: str = Field(..., description="GPU card manufacturer")
    pci_bus_id: str = Field(..., description="PCI bus ID")
    serial: Optional[str] = Field(None, description="GPU serial number")
    memory_total_gb: float = Field(..., description="Total GPU memory in GB", ge=0.0)
    memory_used_gb: float = Field(..., description="Used GPU memory in GB", ge=0.0)
    utilization_percent: int = Field(..., description="GPU utilization percentage", ge=0, le=100)
    temperature_c: int = Field(..., description="GPU temperature in Celsius")
    power_draw_w: float = Field(..., description="Current power draw in watts", ge=0.0)
    power_limit_w: float = Field(..., description="Power limit in watts", ge=0.0)
    model_loaded: Optional[str] = Field(None, description="Name of model currently loaded")


class ContainerStats(BaseModel):
    """Container statistics model."""

    id: str = Field(..., description="Container ID")
    model: str = Field(..., description="Model name running in container")
    runtime: str = Field(..., description="Runtime type (vllm, sglang, llamacpp)")
    gpus: list[int] = Field(default_factory=list, description="List of GPU indices assigned")
    status: str = Field(..., description="Container status")
    uptime_seconds: int = Field(..., description="Container uptime in seconds", ge=0)


class MachineStats(BaseModel):
    """Complete machine statistics model."""

    machine_id: str = Field(..., description="Unique machine identifier")
    hostname: str = Field(..., description="Machine hostname")
    timestamp: datetime = Field(..., description="Timestamp when stats were collected")
    cpu: CPUStats = Field(..., description="CPU statistics")
    memory: MemoryStats = Field(..., description="Memory statistics")
    network: list[NetworkInterfaceStats] = Field(
        default_factory=list, description="Network interface statistics"
    )
    gpus: list[GPUStats] = Field(default_factory=list, description="GPU statistics")
    containers: list[ContainerStats] = Field(
        default_factory=list, description="Container statistics"
    )

    def to_dict(self) -> dict:
        """
        Convert MachineStats to dictionary for JSON serialization.

        Returns:
            dict: Dictionary representation with datetime serialized to ISO format
        """
        data = self.model_dump()
        # Convert datetime to ISO format string for JSON serialization
        data["timestamp"] = self.timestamp.isoformat()
        return data
