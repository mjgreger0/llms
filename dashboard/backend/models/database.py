"""
SQLAlchemy database models for LLM Serve Dashboard.

This module defines all database models following SQLAlchemy 2.0 patterns
with Mapped[] type hints and mapped_column(). Models include both regular
tables and time-series tables (marked for TimescaleDB hypertable conversion).
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dashboard.backend.db.base import Base, TimestampMixin


class Machine(Base):
    """
    GPU servers running daemons.

    Represents physical or virtual machines in the cluster that host
    GPU resources and run the LLM Serve daemon.

    Attributes:
        id: Unique machine identifier (typically hostname or UUID)
        hostname: Machine hostname
        ip_address: IP address for network communication
        first_seen: When this machine was first registered
        last_seen: Last successful health check or stats report
        cpu_model: CPU model name
        cpu_cores: Number of CPU cores
        memory_gb: Total system memory in GB
        notes: Admin notes or comments about this machine
    """
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        doc="Unique machine identifier"
    )

    hostname: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Machine hostname"
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="IP address for network communication"
    )

    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When this machine was first registered"
    )

    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last successful health check or stats report"
    )

    cpu_model: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="CPU model name"
    )

    cpu_cores: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of CPU cores"
    )

    memory_gb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Total system memory in GB"
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Admin notes or comments about this machine"
    )


class Model(Base):
    """
    Base LLM models.

    Represents the base model without quantization (e.g., "qwen2.5-72b-instruct").
    Each model can have multiple quantizations.

    Attributes:
        id: Auto-incrementing primary key
        name: Unique model name (e.g., "qwen2.5-72b-instruct")
        provider: Model provider (e.g., "Qwen", "Meta", "Mistral")
        huggingface_id: HuggingFace model identifier
        base_parameters: Model parameter count (e.g., "72B", "7B")
        added_at: When this model was added to the system
        quantizations: Related quantization versions
    """
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing primary key"
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        doc="Unique model name"
    )

    provider: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Model provider"
    )

    huggingface_id: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        doc="HuggingFace model identifier"
    )

    base_parameters: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Model parameter count (e.g., '72B', '7B')"
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When this model was added to the system"
    )

    # Relationships
    quantizations: Mapped[List["ModelQuantization"]] = relationship(
        "ModelQuantization",
        back_populates="model",
        cascade="all, delete-orphan",
        doc="Related quantization versions"
    )


class ModelQuantization(Base):
    """
    Quantized versions of base models.

    Represents a specific quantization of a base model (e.g., AWQ, Q4_K_M, FP16).
    Each quantization has different file sizes and VRAM requirements.

    Attributes:
        id: Auto-incrementing primary key
        model_id: Foreign key to parent model
        quantization: Quantization type (e.g., "awq", "q4_k_m", "fp16")
        file_path: Path to model files in NFS storage
        file_size_gb: Size of model files in GB
        vram_required_gb: Estimated VRAM required to run this model
        gpu_count: Minimum number of GPUs required
        added_at: When this quantization was added
        model: Parent model relationship
        container_configs: Related container configurations
    """
    __tablename__ = "model_quantizations"
    __table_args__ = (
        UniqueConstraint("model_id", "quantization", name="uq_model_quantization"),
        CheckConstraint("gpu_count >= 1", name="ck_gpu_count_positive"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing primary key"
    )

    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to parent model"
    )

    quantization: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Quantization type (e.g., 'awq', 'q4_k_m', 'fp16')"
    )

    file_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        doc="Path to model files in NFS storage"
    )

    file_size_gb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Size of model files in GB"
    )

    vram_required_gb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Estimated VRAM required to run this model"
    )

    gpu_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
        doc="Minimum number of GPUs required"
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When this quantization was added"
    )

    # Relationships
    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="quantizations",
        doc="Parent model relationship"
    )

    container_configs: Mapped[List["ContainerConfig"]] = relationship(
        "ContainerConfig",
        back_populates="model_quantization",
        cascade="all, delete-orphan",
        doc="Related container configurations"
    )


class ContainerConfig(Base, TimestampMixin):
    """
    Runtime configurations for model deployments.

    Defines how a specific model quantization should be run, including
    runtime engine, parallelism settings, and context length.

    Attributes:
        id: Auto-incrementing primary key
        model_quant_id: Foreign key to model quantization
        runtime: Runtime engine (vllm, sglang, llamacpp)
        context_length: Maximum context window size
        max_parallel: Maximum parallel requests
        tensor_parallel: Tensor parallelism degree
        pipeline_parallel: Pipeline parallelism degree
        extra_args: Additional runtime-specific arguments (JSON)
        model_quantization: Related model quantization
    """
    __tablename__ = "container_configs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing primary key"
    )

    model_quant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("model_quantizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to model quantization"
    )

    runtime: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="vllm",
        doc="Runtime engine (vllm, sglang, llamacpp)"
    )

    context_length: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="8192",
        doc="Maximum context window size"
    )

    max_parallel: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="4",
        doc="Maximum parallel requests"
    )

    tensor_parallel: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
        doc="Tensor parallelism degree"
    )

    pipeline_parallel: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
        doc="Pipeline parallelism degree"
    )

    extra_args: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Additional runtime-specific arguments (JSON)"
    )

    # Relationships
    model_quantization: Mapped["ModelQuantization"] = relationship(
        "ModelQuantization",
        back_populates="container_configs",
        doc="Related model quantization"
    )


class Credential(Base, TimestampMixin):
    """
    Encrypted credentials for external services.

    Stores encrypted credentials (e.g., HuggingFace tokens, API keys)
    using AES-256 encryption with Fernet.

    Attributes:
        id: Auto-incrementing primary key
        name: Unique credential name (e.g., "huggingface")
        encrypted: Encrypted credential value (binary)
    """
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Auto-incrementing primary key"
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        doc="Unique credential name"
    )

    encrypted: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        doc="Encrypted credential value"
    )


class Setting(Base):
    """
    System configuration key-value pairs.

    Stores application settings as JSON values indexed by string keys.

    Attributes:
        key: Setting name (primary key)
        value: Setting value as JSON
        updated_at: When this setting was last modified
    """
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        doc="Setting name"
    )

    value: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Setting value as JSON"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="When this setting was last modified"
    )


class CPUStat(Base):
    """
    Time-series CPU statistics.

    Stores CPU utilization metrics over time for each machine.
    This table will be converted to a TimescaleDB hypertable.

    Attributes:
        time: Timestamp of the measurement
        machine_id: Machine identifier
        cores: Number of CPU cores
        load_percent: CPU load percentage (0-100)
    """
    __tablename__ = "cpu_stats"
    __table_args__ = (
        PrimaryKeyConstraint("time", "machine_id"),
        {"comment": "TimescaleDB hypertable - convert with create_hypertable('cpu_stats', 'time')"},
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Timestamp of the measurement"
    )

    machine_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Machine identifier"
    )

    cores: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of CPU cores"
    )

    load_percent: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="CPU load percentage (0-100)"
    )


class GPUStat(Base):
    """
    Time-series GPU statistics.

    Stores GPU utilization, memory, and temperature metrics over time.
    This table will be converted to a TimescaleDB hypertable.

    Attributes:
        time: Timestamp of the measurement
        machine_id: Machine identifier
        gpu_uuid: GPU UUID (unique identifier from NVIDIA)
        gpu_index: GPU index on the machine
        gpu_name: GPU model name
        memory_total_gb: Total GPU memory in GB
        memory_used_gb: Used GPU memory in GB
        utilization: GPU utilization percentage (0-100)
        temperature_c: GPU temperature in Celsius
        model_loaded: Name of model loaded on this GPU (if any)
    """
    __tablename__ = "gpu_stats"
    __table_args__ = (
        PrimaryKeyConstraint("time", "machine_id", "gpu_uuid"),
        {"comment": "TimescaleDB hypertable - convert with create_hypertable('gpu_stats', 'time')"},
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Timestamp of the measurement"
    )

    machine_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Machine identifier"
    )

    gpu_uuid: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="GPU UUID (unique identifier from NVIDIA)"
    )

    gpu_index: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="GPU index on the machine"
    )

    gpu_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="GPU model name"
    )

    memory_total_gb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Total GPU memory in GB"
    )

    memory_used_gb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Used GPU memory in GB"
    )

    utilization: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="GPU utilization percentage (0-100)"
    )

    temperature_c: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="GPU temperature in Celsius"
    )

    model_loaded: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Name of model loaded on this GPU (if any)"
    )


class MemoryStat(Base):
    """
    Time-series system memory statistics.

    Stores system memory utilization metrics over time for each machine.
    This table will be converted to a TimescaleDB hypertable.

    Attributes:
        time: Timestamp of the measurement
        machine_id: Machine identifier
        total_gb: Total system memory in GB
        used_gb: Used system memory in GB
        available_gb: Available system memory in GB
    """
    __tablename__ = "memory_stats"
    __table_args__ = (
        PrimaryKeyConstraint("time", "machine_id"),
        {"comment": "TimescaleDB hypertable - convert with create_hypertable('memory_stats', 'time')"},
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Timestamp of the measurement"
    )

    machine_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Machine identifier"
    )

    total_gb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Total system memory in GB"
    )

    used_gb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Used system memory in GB"
    )

    available_gb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Available system memory in GB"
    )
