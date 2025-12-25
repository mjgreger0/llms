"""
VRAM estimation utilities for LLM model deployment.

This module provides functions to estimate VRAM requirements for running
LLM models with various quantization types. The estimates use a formula
based on model parameters and bits per parameter, with overhead for
KV cache, activations, and runtime overhead.

Formula:
    VRAM (GB) = (params_billions * bits_per_param / 8) * overhead_multiplier

The default overhead multiplier is 1.2 (20%) to account for:
- KV cache memory during inference
- Activation memory
- Runtime buffers and overhead

Note: These are estimates. Actual VRAM usage may vary based on:
- Context length (longer contexts use more KV cache)
- Batch size / concurrent requests
- Specific model architecture
- Runtime implementation (vLLM, SGLang, etc.)

For production deployments, measure actual usage and adjust if needed.
"""

import re
from typing import Optional


# Quantization type to bits per parameter mapping
QUANTIZATION_BITS: dict[str, int] = {
    # Full precision
    "fp32": 32,
    "float32": 32,

    # Half precision (most common for inference)
    "fp16": 16,
    "float16": 16,
    "bf16": 16,
    "bfloat16": 16,

    # 8-bit quantization
    "int8": 8,
    "q8": 8,
    "q8_0": 8,
    "w8a8": 8,

    # 6-bit quantization
    "q6_k": 6,

    # 5-bit quantization
    "q5_k_m": 5,
    "q5_k_s": 5,
    "q5_0": 5,
    "q5_1": 5,

    # 4-bit quantization (most common for efficient inference)
    "int4": 4,
    "q4": 4,
    "q4_0": 4,
    "q4_1": 4,
    "q4_k_m": 4,
    "q4_k_s": 4,
    "awq": 4,
    "gptq": 4,
    "gguf": 4,  # Default for GGUF, though it can vary

    # 3-bit quantization
    "q3_k_m": 3,
    "q3_k_s": 3,

    # 2-bit quantization
    "q2_k": 2,
}

# Default overhead multiplier (20% for KV cache, activations, etc.)
DEFAULT_OVERHEAD_MULTIPLIER = 1.2


def parse_parameter_count(params: str) -> float:
    """
    Parse parameter count string to billions.

    Accepts formats like "72B", "7B", "72", "7.5B", "1.3b", etc.

    Args:
        params: Parameter count string (e.g., "72B", "7B", "7.5B")

    Returns:
        Parameter count in billions (float)

    Raises:
        ValueError: If the string cannot be parsed

    Examples:
        >>> parse_parameter_count("72B")
        72.0
        >>> parse_parameter_count("7.5B")
        7.5
        >>> parse_parameter_count("7")
        7.0
        >>> parse_parameter_count("1.3b")
        1.3
    """
    if not params:
        raise ValueError("Parameter string cannot be empty")

    # Normalize: strip whitespace and convert to uppercase
    normalized = params.strip().upper()

    # Pattern to match number with optional decimal, optionally followed by 'B'
    pattern = r'^(\d+\.?\d*)\s*B?$'
    match = re.match(pattern, normalized)

    if not match:
        raise ValueError(f"Cannot parse parameter count from '{params}'")

    return float(match.group(1))


def get_bits_for_quantization(quantization: str) -> int:
    """
    Get the bits per parameter for a quantization type.

    Args:
        quantization: Quantization type name (case-insensitive)

    Returns:
        Bits per parameter

    Raises:
        ValueError: If quantization type is unknown

    Examples:
        >>> get_bits_for_quantization("fp16")
        16
        >>> get_bits_for_quantization("AWQ")
        4
        >>> get_bits_for_quantization("q8_0")
        8
    """
    normalized = quantization.lower().strip()

    if normalized in QUANTIZATION_BITS:
        return QUANTIZATION_BITS[normalized]

    raise ValueError(
        f"Unknown quantization type: '{quantization}'. "
        f"Known types: {', '.join(sorted(QUANTIZATION_BITS.keys()))}"
    )


def estimate_vram_gb(
    base_parameters: str,
    quantization: str,
    overhead_multiplier: float = DEFAULT_OVERHEAD_MULTIPLIER
) -> float:
    """
    Estimate VRAM requirements for a model with given quantization.

    Uses the formula: VRAM = (params_B * bits / 8) * overhead_multiplier

    Args:
        base_parameters: Parameter count string (e.g., "72B", "7B")
        quantization: Quantization type (e.g., "awq", "fp16", "q4_k_m")
        overhead_multiplier: Multiplier for overhead (default 1.2 = 20%)

    Returns:
        Estimated VRAM requirement in GB

    Raises:
        ValueError: If parameters or quantization cannot be parsed

    Examples:
        >>> estimate_vram_gb("72B", "awq")  # 72 * 4 / 8 * 1.2 = 43.2
        43.2
        >>> estimate_vram_gb("7B", "fp16")  # 7 * 16 / 8 * 1.2 = 16.8
        16.8
        >>> estimate_vram_gb("8B", "q4_k_m")  # 8 * 4 / 8 * 1.2 = 4.8
        4.8

    Reference VRAM estimates (with 1.2x overhead):
        - 72B AWQ:    43.2 GB (2x 24GB GPUs)
        - 72B FP16:  172.8 GB (4x 48GB GPUs)
        - 32B AWQ:   19.2 GB (1x 24GB GPU)
        - 32B FP16:  76.8 GB (2x 48GB GPUs)
        - 7B AWQ:     4.2 GB (1x GPU)
        - 7B FP16:   16.8 GB (1x 24GB GPU)
        - 7B Q8_0:    8.4 GB (1x GPU)
    """
    params_billions = parse_parameter_count(base_parameters)
    bits = get_bits_for_quantization(quantization)

    # Calculate VRAM: (params * bits / 8) * overhead
    vram_gb = (params_billions * bits / 8) * overhead_multiplier

    # Round to 1 decimal place for cleanliness
    return round(vram_gb, 1)


def calculate_kv_cache_gb(
    layers: int,
    heads: int,
    head_dim: int,
    context_length: int,
    batch_size: int = 1,
    bytes_per_element: int = 2
) -> float:
    """
    Calculate additional VRAM needed for KV cache based on context length.

    This is informational and helps understand how context length affects
    memory usage. The base estimate_vram_gb already includes some overhead
    for KV cache, but this function shows the specific contribution.

    Formula:
        KV cache = layers * 2 * heads * head_dim * context_length * batch_size * bytes

    The factor of 2 is for both K and V tensors.

    Args:
        layers: Number of transformer layers
        heads: Number of attention heads (KV heads for GQA models)
        head_dim: Dimension per attention head
        context_length: Maximum context length
        batch_size: Number of concurrent sequences (default 1)
        bytes_per_element: Bytes per KV element (2 for FP16, 4 for FP32)

    Returns:
        KV cache memory in GB

    Examples:
        # Llama 3.1 8B architecture (32 layers, 8 KV heads, 128 dim)
        >>> calculate_kv_cache_gb(32, 8, 128, 8192)
        0.5
        >>> calculate_kv_cache_gb(32, 8, 128, 131072)  # 128K context
        8.0

        # Qwen 2.5 72B architecture (80 layers, 8 KV heads, 128 dim)
        >>> calculate_kv_cache_gb(80, 8, 128, 32768)
        5.0

    Note:
        KV heads may be different from attention heads in GQA models.
        For example, Llama 3.1 8B uses 32 attention heads but only 8 KV heads.
    """
    # Calculate total bytes
    kv_bytes = (
        layers * 2 * heads * head_dim * context_length * batch_size * bytes_per_element
    )

    # Convert to GB
    kv_gb = kv_bytes / (1024 ** 3)

    return round(kv_gb, 1)


def suggest_gpu_count(vram_gb: float, gpu_memory_gb: float = 24.0) -> int:
    """
    Suggest number of GPUs needed based on VRAM requirements.

    Args:
        vram_gb: Estimated VRAM requirement in GB
        gpu_memory_gb: Memory per GPU in GB (default 24GB for RTX 3090/4090)

    Returns:
        Suggested number of GPUs (must be power of 2 for tensor parallelism)

    Examples:
        >>> suggest_gpu_count(20.0)  # Fits in 1 GPU
        1
        >>> suggest_gpu_count(30.0)  # Needs 2 GPUs
        2
        >>> suggest_gpu_count(80.0)  # Needs 4 GPUs
        4
        >>> suggest_gpu_count(200.0)  # Needs 8 GPUs
        8
    """
    if vram_gb <= gpu_memory_gb:
        return 1

    # Calculate minimum GPUs needed
    min_gpus = int(vram_gb / gpu_memory_gb) + 1

    # Round up to power of 2 (required for tensor parallelism)
    power = 1
    while power < min_gpus:
        power *= 2

    return power


def format_vram_summary(
    base_parameters: str,
    quantization: str,
    gpu_memory_gb: float = 24.0
) -> str:
    """
    Format a human-readable summary of VRAM requirements.

    Args:
        base_parameters: Parameter count string (e.g., "72B")
        quantization: Quantization type (e.g., "awq")
        gpu_memory_gb: Memory per GPU in GB (default 24GB)

    Returns:
        Formatted summary string

    Examples:
        >>> print(format_vram_summary("72B", "awq"))
        72B awq: 43.2 GB VRAM (2x 24GB GPUs)
    """
    vram = estimate_vram_gb(base_parameters, quantization)
    gpus = suggest_gpu_count(vram, gpu_memory_gb)

    if gpus == 1:
        gpu_str = "1 GPU"
    else:
        gpu_str = f"{gpus}x {int(gpu_memory_gb)}GB GPUs"

    return f"{base_parameters} {quantization}: {vram} GB VRAM ({gpu_str})"
