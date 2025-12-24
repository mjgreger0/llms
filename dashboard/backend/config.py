"""
Dashboard backend configuration module.

Loads configuration from environment variables using Pydantic v2 BaseSettings.
All settings have sensible defaults except for required security values.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Dashboard backend configuration loaded from environment variables.

    Environment Variables:
        LLM_SERVE_ENCRYPTION_KEY: Secret key for encrypting credentials (REQUIRED, min 32 chars)
        DATABASE_URL: PostgreSQL connection string (default: postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve)
        DATABASE_POOL_SIZE: Connection pool size (default: 20)
        DATABASE_MAX_OVERFLOW: Max overflow connections (default: 10)
        HOST: Server bind host (default: 0.0.0.0)
        PORT: Server bind port (default: 8080)
        ALLOWED_NETWORKS: Comma-separated CIDR networks for CORS (default: 192.168.0.0/24)
        MODEL_PATH: Path to model storage (default: /data/projects/ai/models)
        METRICS_RETENTION_DAYS: Days to retain metrics in TimescaleDB (default: 30)
        DEFAULT_REQUEST_TIMEOUT_SECONDS: Default timeout for inference requests (default: 60)
        HEALTH_CHECK_INTERVAL_SECONDS: Interval for container health checks (default: 1)
        LOG_LEVEL: Logging level (default: INFO)
        LOG_FORMAT: Log format - json or text (default: json)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required - Security
    llm_serve_encryption_key: str = Field(
        ...,
        description="Secret key for encrypting stored credentials (minimum 32 characters)",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve",
        description="Async PostgreSQL connection URL",
    )
    database_pool_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Database connection pool size",
    )
    database_max_overflow: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Maximum overflow connections beyond pool size",
    )

    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="Server bind host",
    )
    port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Server bind port",
    )

    # Network Configuration
    allowed_networks: str = Field(
        default="192.168.0.0/24",
        description="Comma-separated CIDR networks allowed for CORS",
    )

    # Storage Configuration
    model_path: str = Field(
        default="/data/projects/ai/models",
        description="Path to shared model storage (NFS mount)",
    )

    # Metrics Configuration
    metrics_retention_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to retain metrics in TimescaleDB",
    )

    # Request Handling
    default_request_timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Default timeout for inference requests",
    )
    health_check_interval_seconds: int = Field(
        default=1,
        ge=1,
        le=60,
        description="Interval between container health checks",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_format: str = Field(
        default="json",
        description="Log output format (json or text)",
    )

    # Application Metadata
    app_name: str = Field(
        default="LLM Serve Dashboard",
        description="Application name for logging and API docs",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application version",
    )

    @field_validator("llm_serve_encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate encryption key is at least 32 characters for security."""
        if len(v) < 32:
            raise ValueError(
                f"LLM_SERVE_ENCRYPTION_KEY must be at least 32 characters, got {len(v)}"
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a known value."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got {v}"
            )
        return v_upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format is json or text."""
        v_lower = v.lower()
        if v_lower not in {"json", "text"}:
            raise ValueError(
                f"LOG_FORMAT must be 'json' or 'text', got {v}"
            )
        return v_lower

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL uses asyncpg driver."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use asyncpg driver (postgresql+asyncpg://...)"
            )
        return v

    def get_allowed_origins(self) -> list[str]:
        """
        Parse allowed networks into CORS origin patterns.

        Returns:
            List of origin patterns for CORS configuration.
            For development, allows all origins from the network.
        """
        # Split comma-separated networks
        networks = [n.strip() for n in self.allowed_networks.split(",")]

        # For now, allow all origins (will be refined with actual network filtering)
        # This is a placeholder - proper implementation would convert CIDR to origin patterns
        origins = []
        for network in networks:
            if network:
                # Simplified: allow all http/https from this network
                # Full implementation would validate IP ranges
                origins.append(f"http://{network}")
                origins.append(f"https://{network}")

        return origins if origins else ["*"]


class RouterConfig(BaseSettings):
    """Router-specific configuration for Phase 5 request routing."""

    model_config = SettingsConfigDict(
        env_prefix="ROUTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Timeout settings
    default_loading_timeout: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Default loading timeout in seconds"
    )
    default_inference_timeout: int = Field(
        default=120,
        ge=30,
        le=3600,
        description="Default inference timeout in seconds"
    )

    # Keepalive settings
    keepalive_interval: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="SSE keepalive interval in seconds"
    )

    # Capacity settings
    max_gpus_per_machine: int = Field(
        default=8,
        ge=1,
        le=16,
        description="Maximum GPUs per machine for multi-machine detection"
    )

    # Queue settings
    max_queue_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum requests per model queue"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    This prevents repeated environment variable parsing and validation.

    Returns:
        Cached Settings instance.

    Raises:
        ValidationError: If required settings are missing or invalid.
    """
    return Settings()


@lru_cache
def get_router_config() -> RouterConfig:
    """
    Get cached router configuration instance.

    Uses lru_cache to ensure configuration is only loaded once.
    This prevents repeated environment variable parsing and validation.

    Returns:
        Cached RouterConfig instance.

    Raises:
        ValidationError: If router settings are invalid.
    """
    return RouterConfig()


# Convenience export for direct import
settings = get_settings()
router_config = get_router_config()
