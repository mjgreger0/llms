"""
Utility functions for LLM Serve Dashboard.

This package provides utility functions for common operations
across the dashboard backend.
"""

from dashboard.backend.utils.vram import (
    QUANTIZATION_BITS,
    calculate_kv_cache_gb,
    estimate_vram_gb,
    format_vram_summary,
    get_bits_for_quantization,
    parse_parameter_count,
    suggest_gpu_count,
)

__all__ = [
    "QUANTIZATION_BITS",
    "calculate_kv_cache_gb",
    "estimate_vram_gb",
    "format_vram_summary",
    "get_bits_for_quantization",
    "parse_parameter_count",
    "suggest_gpu_count",
]
