"""Data models for container configuration and commands."""

from typing import Optional

from pydantic import BaseModel, Field


class ContainerConfig(BaseModel):
    """Container configuration model for launching LLM containers."""

    model_quant: str = Field(..., description="Model quantization identifier")
    model_path: str = Field(..., description="Path to model files")
    image: str = Field(..., description="Container image to use")
    runtime: str = Field(..., description="Runtime type (vllm, sglang, llamacpp)")
    gpus: list[int] = Field(default_factory=list, description="List of GPU indices to assign")
    context_length: int = Field(..., description="Maximum context length", ge=1)
    max_parallel: int = Field(..., description="Maximum parallel sequences", ge=1)
    tensor_parallel: int = Field(..., description="Tensor parallelism degree", ge=1)
    pipeline_parallel: int = Field(..., description="Pipeline parallelism degree", ge=1)
    extra_args: Optional[dict] = Field(
        None, description="Additional runtime-specific arguments"
    )
