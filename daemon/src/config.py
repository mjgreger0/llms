"""Configuration Module - Environment Variable Loading and Validation."""

import socket
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """
    Daemon configuration loaded from environment variables.

    Uses Pydantic Settings for automatic environment variable loading
    and validation. All UPPERCASE fields are loaded from environment.
    """

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
    )

    # Required Configuration
    DASHBOARD_URL: str = Field(
        ...,
        description="WebSocket URL of the Dashboard control plane (required)",
        examples=["ws://dashboard.local:8080/ws/daemon"]
    )

    # Machine Identity
    MACHINE_ID: str = Field(
        default_factory=lambda: socket.gethostname(),
        description="Unique identifier for this machine (auto-generated from hostname if not set)"
    )

    # Host Filesystem Paths (for containerized daemon)
    PROC_PATH: Path = Field(
        default=Path("/host/proc"),
        description="Path to host's /proc directory (for stats collection)"
    )

    SYS_PATH: Path = Field(
        default=Path("/host/sys"),
        description="Path to host's /sys directory (for hardware info)"
    )

    # Container Runtime Configuration
    PODMAN_SOCKET: Path = Field(
        default=Path("/run/podman/podman.sock"),
        description="Path to Podman socket for container management"
    )

    MODEL_PATH: Path = Field(
        default=Path("/models"),
        description="Path to NFS-mounted model storage directory"
    )

    # Timing Configuration
    STATS_INTERVAL_SECONDS: int = Field(
        default=6,
        description="Interval between stats collection cycles",
        ge=1,
        le=3600
    )

    HEALTH_CHECK_INTERVAL_SECONDS: int = Field(
        default=5,
        description="Interval between container health checks",
        ge=1,
        le=300
    )

    # Logging Configuration
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level for daemon output"
    )

    LOG_FORMAT: Literal["json", "console"] = Field(
        default="json",
        description="Log output format (json for production, console for development)"
    )

    @field_validator("PROC_PATH", "SYS_PATH", "PODMAN_SOCKET", "MODEL_PATH")
    @classmethod
    def validate_absolute_path(cls, v: Path, info) -> Path:
        """Ensure all path configurations are absolute paths."""
        if not v.is_absolute():
            raise ValueError(
                f"{info.field_name} must be an absolute path, got: {v}"
            )
        return v

    @field_validator("STATS_INTERVAL_SECONDS", "HEALTH_CHECK_INTERVAL_SECONDS")
    @classmethod
    def validate_positive_interval(cls, v: int, info) -> int:
        """Ensure interval values are positive."""
        if v <= 0:
            raise ValueError(
                f"{info.field_name} must be positive, got: {v}"
            )
        return v


# Global config instance - loaded once at module import
config = Config()
