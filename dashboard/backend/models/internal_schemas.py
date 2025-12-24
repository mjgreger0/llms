"""
Internal request/response schemas for the LLM Serve Dashboard.

This module contains internal schemas used for request processing, model routing,
GPU requirements, and container endpoint management. These are not exposed in the
public API but used internally for orchestration.
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from dashboard.backend.models.openai_schemas import (
    ChatCompletionRequest,
    CompletionRequest,
)


# ============================================================================
# Internal Request Schemas
# ============================================================================

class InferenceRequest(BaseModel):
    """Internal wrapper for inference requests with tracking metadata.

    Wraps OpenAI-compatible requests with additional metadata needed for
    request routing, queueing, and timeout handling.
    """
    request_id: str = Field(description="Unique identifier for this request")
    model: str = Field(description="Model name to use for inference")
    request: Union[ChatCompletionRequest, CompletionRequest] = Field(
        description="The actual OpenAI-compatible request"
    )
    enqueue_time: datetime = Field(description="When the request was enqueued")
    timeout_seconds: float = Field(default=300.0, description="Request timeout in seconds")
    stream: bool = Field(description="Whether this is a streaming request")

    model_config = ConfigDict(from_attributes=True)


class RequestContext(BaseModel):
    """Context for tracking an in-flight request.

    Maintains state for request processing including synchronization primitives
    for async handling and result storage.
    """
    request_id: str = Field(description="Unique identifier for this request")
    response_event: Optional[Any] = Field(None, description="asyncio.Event for response signaling")
    stream_queue: Optional[Any] = Field(None, description="asyncio.Queue for streaming chunks")
    error: Optional[str] = Field(None, description="Error message if request failed")
    result: Optional[Any] = Field(None, description="Final result for non-streaming requests")

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


# ============================================================================
# Model Quantization Parser
# ============================================================================

@dataclass
class ModelQuant:
    """Model name and quantization parser.

    Parses model strings to extract the base model name and quantization suffix.
    Supports common quantization formats like AWQ, GPTQ, GGUF quantizations, etc.

    Example:
        >>> mq = ModelQuant.parse("qwen2.5-72b-instruct-awq")
        >>> mq.model_name
        'qwen2.5-72b-instruct'
        >>> mq.quantization
        'awq'
    """
    model_name: str
    quantization: Optional[str]

    # Known quantization suffixes to extract
    KNOWN_QUANTS = [
        "awq",
        "gptq",
        "q4_k_m",
        "q8_0",
        "fp8",
        "fp16",
        "bnb",
        "exl2",
    ]

    @classmethod
    def parse(cls, model_string: str) -> "ModelQuant":
        """Parse a model string to extract model name and quantization.

        Args:
            model_string: Full model identifier (e.g., "qwen2.5-72b-instruct-awq")

        Returns:
            ModelQuant instance with parsed model_name and quantization

        Examples:
            >>> ModelQuant.parse("llama-3-70b-awq")
            ModelQuant(model_name='llama-3-70b', quantization='awq')

            >>> ModelQuant.parse("qwen2.5-72b-instruct")
            ModelQuant(model_name='qwen2.5-72b-instruct', quantization=None)

            >>> ModelQuant.parse("mistral-7b-q4_k_m")
            ModelQuant(model_name='mistral-7b', quantization='q4_k_m')
        """
        model_lower = model_string.lower()

        # Try to match known quantization suffixes
        for quant in cls.KNOWN_QUANTS:
            # Match quant at end of string, preceded by hyphen or underscore
            pattern = rf"[-_]{quant}$"
            if re.search(pattern, model_lower):
                # Remove the quantization suffix from model name
                model_name = re.sub(pattern, "", model_string, flags=re.IGNORECASE)
                return cls(model_name=model_name, quantization=quant)

        # No quantization found
        return cls(model_name=model_string, quantization=None)


# ============================================================================
# GPU Requirements
# ============================================================================

@dataclass
class GPURequirement:
    """GPU resource requirements for a model.

    Specifies the GPU resources needed to run a specific model configuration,
    including VRAM, GPU count, and parallelization settings.

    Attributes:
        vram_required_gb: Minimum VRAM per GPU in gigabytes
        gpu_count: Total number of GPUs required
        tensor_parallel: Tensor parallelism degree (splits model across GPUs)
        pipeline_parallel: Pipeline parallelism degree (splits layers across GPUs)
        multi_machine: Whether this requires multiple machines
    """
    vram_required_gb: float
    gpu_count: int
    tensor_parallel: int = 1
    pipeline_parallel: int = 1
    multi_machine: bool = False

    def __post_init__(self):
        """Validate GPU requirements."""
        if self.vram_required_gb < 0:
            raise ValueError("vram_required_gb must be non-negative")
        if self.gpu_count < 1:
            raise ValueError("gpu_count must be at least 1")
        if self.tensor_parallel < 1:
            raise ValueError("tensor_parallel must be at least 1")
        if self.pipeline_parallel < 1:
            raise ValueError("pipeline_parallel must be at least 1")

        # Multi-machine should be true if parallelism exceeds single-machine GPU count
        total_parallel = self.tensor_parallel * self.pipeline_parallel
        if total_parallel > 8:  # Assume max 8 GPUs per machine
            self.multi_machine = True


# ============================================================================
# Container Endpoint
# ============================================================================

@dataclass
class ContainerEndpoint:
    """Endpoint information for a running container.

    Tracks the network location and health check URL for a running model container.

    Attributes:
        machine_id: Identifier of the machine hosting the container
        host: Hostname or IP address
        port: Port number the container is listening on
        health_url: Full URL for health checks
    """
    machine_id: str
    host: str
    port: int
    health_url: str

    @property
    def inference_url(self) -> str:
        """Get the full inference API URL.

        Returns:
            Full URL to the chat completions endpoint
        """
        return f"http://{self.host}:{self.port}/v1/chat/completions"

    @property
    def completions_url(self) -> str:
        """Get the full text completions API URL.

        Returns:
            Full URL to the completions endpoint
        """
        return f"http://{self.host}:{self.port}/v1/completions"

    @property
    def base_url(self) -> str:
        """Get the base URL for the container.

        Returns:
            Base URL without path
        """
        return f"http://{self.host}:{self.port}"

    def __post_init__(self):
        """Validate endpoint configuration."""
        if not self.machine_id:
            raise ValueError("machine_id cannot be empty")
        if not self.host:
            raise ValueError("host cannot be empty")
        if self.port < 1 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if not self.health_url:
            raise ValueError("health_url cannot be empty")
