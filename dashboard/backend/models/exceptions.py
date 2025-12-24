"""Custom exceptions for the router."""

from typing import Optional


class RouterError(Exception):
    """Base exception for router errors."""

    def __init__(self, message: str, code: str = "router_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class ModelNotFoundError(RouterError):
    """Model not found in registry."""

    def __init__(self, model: str, quantization: Optional[str] = None):
        model_name = f"{model}-{quantization}" if quantization else model
        super().__init__(
            message=f"Model '{model_name}' not found",
            code="model_not_found"
        )
        self.model = model
        self.quantization = quantization


class InsufficientCapacityError(RouterError):
    """Not enough GPU capacity available."""

    def __init__(self, required_vram: float, available_vram: float):
        super().__init__(
            message=f"Insufficient GPU capacity: need {required_vram:.1f}GB, have {available_vram:.1f}GB available",
            code="insufficient_capacity"
        )
        self.required_vram = required_vram
        self.available_vram = available_vram


class ModelLoadError(RouterError):
    """Failed to load model."""

    def __init__(self, model: str, reason: str):
        super().__init__(
            message=f"Failed to load model '{model}': {reason}",
            code="model_load_error"
        )
        self.model = model
        self.reason = reason


class ContainerTimeoutError(RouterError):
    """Container operation timed out."""

    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout_seconds}s",
            code="timeout"
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class ContainerNotReadyError(RouterError):
    """Container not in ready state."""

    def __init__(self, container_id: str, status: str):
        super().__init__(
            message=f"Container '{container_id}' not ready: status={status}",
            code="container_not_ready"
        )
        self.container_id = container_id
        self.status = status
