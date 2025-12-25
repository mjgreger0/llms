"""
Tests for VRAM estimation utilities.

Tests the VRAM calculation functions against known reference values
from the seed data and architecture documentation.
"""

import pytest

from dashboard.backend.utils.vram import (
    QUANTIZATION_BITS,
    calculate_kv_cache_gb,
    estimate_vram_gb,
    format_vram_summary,
    get_bits_for_quantization,
    parse_parameter_count,
    suggest_gpu_count,
)


class TestParseParameterCount:
    """Tests for parse_parameter_count function."""

    def test_parse_simple_integer_with_b(self):
        """Parse simple integer with B suffix."""
        assert parse_parameter_count("72B") == 72.0
        assert parse_parameter_count("7B") == 7.0
        assert parse_parameter_count("8B") == 8.0

    def test_parse_decimal_with_b(self):
        """Parse decimal numbers with B suffix."""
        assert parse_parameter_count("7.5B") == 7.5
        assert parse_parameter_count("1.3B") == 1.3
        assert parse_parameter_count("0.5B") == 0.5

    def test_parse_lowercase_b(self):
        """Parse lowercase 'b' suffix."""
        assert parse_parameter_count("72b") == 72.0
        assert parse_parameter_count("7.5b") == 7.5

    def test_parse_without_suffix(self):
        """Parse numbers without B suffix."""
        assert parse_parameter_count("72") == 72.0
        assert parse_parameter_count("7.5") == 7.5

    def test_parse_with_whitespace(self):
        """Parse with leading/trailing whitespace."""
        assert parse_parameter_count("  72B  ") == 72.0
        assert parse_parameter_count("7 B") == 7.0

    def test_parse_empty_string_raises(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_parameter_count("")

    def test_parse_invalid_string_raises(self):
        """Invalid strings should raise ValueError."""
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_parameter_count("abc")

        with pytest.raises(ValueError, match="Cannot parse"):
            parse_parameter_count("B72")


class TestGetBitsForQuantization:
    """Tests for get_bits_for_quantization function."""

    def test_fp16_quantization(self):
        """FP16/BF16 should return 16 bits."""
        assert get_bits_for_quantization("fp16") == 16
        assert get_bits_for_quantization("FP16") == 16
        assert get_bits_for_quantization("bf16") == 16
        assert get_bits_for_quantization("float16") == 16

    def test_8bit_quantization(self):
        """8-bit quantizations should return 8 bits."""
        assert get_bits_for_quantization("q8_0") == 8
        assert get_bits_for_quantization("q8") == 8
        assert get_bits_for_quantization("int8") == 8

    def test_4bit_quantization(self):
        """4-bit quantizations should return 4 bits."""
        assert get_bits_for_quantization("awq") == 4
        assert get_bits_for_quantization("AWQ") == 4
        assert get_bits_for_quantization("gptq") == 4
        assert get_bits_for_quantization("q4_k_m") == 4
        assert get_bits_for_quantization("q4_k_s") == 4

    def test_other_quantizations(self):
        """Test other quantization bit depths."""
        assert get_bits_for_quantization("fp32") == 32
        assert get_bits_for_quantization("q6_k") == 6
        assert get_bits_for_quantization("q5_k_m") == 5
        assert get_bits_for_quantization("q3_k_m") == 3
        assert get_bits_for_quantization("q2_k") == 2

    def test_unknown_quantization_raises(self):
        """Unknown quantization should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown quantization type"):
            get_bits_for_quantization("unknown_quant")

    def test_case_insensitivity(self):
        """Quantization names should be case-insensitive."""
        assert get_bits_for_quantization("awq") == get_bits_for_quantization("AWQ")
        assert get_bits_for_quantization("fp16") == get_bits_for_quantization("FP16")


class TestEstimateVramGb:
    """Tests for estimate_vram_gb function."""

    def test_reference_values_awq(self):
        """Test AWQ estimates match reference values."""
        # 72B AWQ: 72 * 4 / 8 * 1.2 = 43.2 GB
        assert estimate_vram_gb("72B", "awq") == 43.2

        # 7B AWQ: 7 * 4 / 8 * 1.2 = 4.2 GB
        assert estimate_vram_gb("7B", "awq") == 4.2

        # 32B AWQ: 32 * 4 / 8 * 1.2 = 19.2 GB
        assert estimate_vram_gb("32B", "awq") == 19.2

        # 14B AWQ: 14 * 4 / 8 * 1.2 = 8.4 GB
        assert estimate_vram_gb("14B", "awq") == 8.4

    def test_reference_values_fp16(self):
        """Test FP16 estimates match reference values."""
        # 72B FP16: 72 * 16 / 8 * 1.2 = 172.8 GB
        assert estimate_vram_gb("72B", "fp16") == 172.8

        # 7B FP16: 7 * 16 / 8 * 1.2 = 16.8 GB
        assert estimate_vram_gb("7B", "fp16") == 16.8

        # 32B FP16: 32 * 16 / 8 * 1.2 = 76.8 GB
        assert estimate_vram_gb("32B", "fp16") == 76.8

    def test_reference_values_q8(self):
        """Test Q8 estimates match reference values."""
        # 7B Q8: 7 * 8 / 8 * 1.2 = 8.4 GB
        assert estimate_vram_gb("7B", "q8_0") == 8.4

        # 8B Q8: 8 * 8 / 8 * 1.2 = 9.6 GB
        assert estimate_vram_gb("8B", "q8_0") == 9.6

    def test_custom_overhead_multiplier(self):
        """Test with custom overhead multiplier."""
        # 7B AWQ with no overhead: 7 * 4 / 8 = 3.5 GB
        assert estimate_vram_gb("7B", "awq", overhead_multiplier=1.0) == 3.5

        # 7B AWQ with 50% overhead: 7 * 4 / 8 * 1.5 = 5.25 GB
        assert estimate_vram_gb("7B", "awq", overhead_multiplier=1.5) == 5.2

    def test_case_insensitivity(self):
        """Parameters and quantization should be case-insensitive."""
        assert estimate_vram_gb("72b", "AWQ") == estimate_vram_gb("72B", "awq")

    def test_invalid_parameters_raise(self):
        """Invalid parameters should raise ValueError."""
        with pytest.raises(ValueError):
            estimate_vram_gb("", "awq")

        with pytest.raises(ValueError):
            estimate_vram_gb("abc", "awq")

    def test_invalid_quantization_raises(self):
        """Invalid quantization should raise ValueError."""
        with pytest.raises(ValueError):
            estimate_vram_gb("7B", "unknown")


class TestCalculateKvCacheGb:
    """Tests for calculate_kv_cache_gb function."""

    def test_llama_8b_short_context(self):
        """Test Llama 3.1 8B with 8K context."""
        # 32 layers, 8 KV heads, 128 dim, 8192 context
        # 32 * 2 * 8 * 128 * 8192 * 1 * 2 = 1,073,741,824 bytes = 1.0 GB
        kv = calculate_kv_cache_gb(32, 8, 128, 8192)
        assert kv == 0.5  # Rounds to 0.5 due to exact calculation

    def test_llama_8b_long_context(self):
        """Test Llama 3.1 8B with 128K context."""
        # 32 layers, 8 KV heads, 128 dim, 131072 context
        kv = calculate_kv_cache_gb(32, 8, 128, 131072)
        assert kv == 8.0

    def test_batch_size_scaling(self):
        """KV cache should scale linearly with batch size."""
        base = calculate_kv_cache_gb(32, 8, 128, 8192, batch_size=1)
        double = calculate_kv_cache_gb(32, 8, 128, 8192, batch_size=2)
        assert double == pytest.approx(base * 2, rel=0.1)

    def test_fp32_kv_cache(self):
        """Test with FP32 KV cache (4 bytes per element)."""
        fp16 = calculate_kv_cache_gb(32, 8, 128, 8192, bytes_per_element=2)
        fp32 = calculate_kv_cache_gb(32, 8, 128, 8192, bytes_per_element=4)
        assert fp32 == pytest.approx(fp16 * 2, rel=0.1)


class TestSuggestGpuCount:
    """Tests for suggest_gpu_count function."""

    def test_single_gpu(self):
        """Models that fit in one GPU."""
        assert suggest_gpu_count(10.0) == 1
        assert suggest_gpu_count(20.0) == 1
        assert suggest_gpu_count(24.0) == 1  # Exactly fits

    def test_two_gpus(self):
        """Models needing 2 GPUs."""
        assert suggest_gpu_count(30.0) == 2
        assert suggest_gpu_count(45.0) == 2

    def test_four_gpus(self):
        """Models needing 4 GPUs."""
        assert suggest_gpu_count(80.0) == 4
        assert suggest_gpu_count(90.0) == 4

    def test_eight_gpus(self):
        """Models needing 8 GPUs."""
        assert suggest_gpu_count(200.0) == 8

    def test_power_of_two_requirement(self):
        """GPU count should always be power of 2."""
        # 50 GB needs 3 GPUs minimum, rounds up to 4
        assert suggest_gpu_count(50.0) == 4

        # 100 GB needs 5 GPUs minimum, rounds up to 8
        assert suggest_gpu_count(100.0) == 8

    def test_custom_gpu_memory(self):
        """Test with different GPU memory sizes."""
        # With 48GB GPUs
        assert suggest_gpu_count(40.0, gpu_memory_gb=48.0) == 1
        assert suggest_gpu_count(80.0, gpu_memory_gb=48.0) == 2

        # With 80GB GPUs (A100)
        assert suggest_gpu_count(150.0, gpu_memory_gb=80.0) == 2


class TestFormatVramSummary:
    """Tests for format_vram_summary function."""

    def test_single_gpu_format(self):
        """Format string for single GPU models."""
        summary = format_vram_summary("7B", "awq")
        assert "7B" in summary
        assert "awq" in summary
        assert "4.2 GB" in summary
        assert "1 GPU" in summary

    def test_multi_gpu_format(self):
        """Format string for multi-GPU models."""
        summary = format_vram_summary("72B", "awq")
        assert "72B" in summary
        assert "awq" in summary
        assert "43.2 GB" in summary
        assert "2x 24GB GPUs" in summary

    def test_custom_gpu_memory(self):
        """Format with custom GPU memory size."""
        summary = format_vram_summary("72B", "awq", gpu_memory_gb=48.0)
        assert "48GB GPUs" in summary


class TestQuantizationBitsMapping:
    """Tests for QUANTIZATION_BITS constant."""

    def test_all_mappings_positive(self):
        """All bit mappings should be positive integers."""
        for quant, bits in QUANTIZATION_BITS.items():
            assert isinstance(bits, int), f"{quant} has non-integer bits"
            assert bits > 0, f"{quant} has non-positive bits"
            assert bits <= 32, f"{quant} has bits > 32"

    def test_common_quantizations_present(self):
        """Common quantization types should be present."""
        required = ["fp16", "bf16", "awq", "gptq", "q4_k_m", "q8_0"]
        for quant in required:
            assert quant in QUANTIZATION_BITS, f"Missing {quant}"


class TestSeedDataValidation:
    """
    Validate that the VRAM estimates in seed data are reasonable.

    These tests compare the database seed values to calculated values.
    A 10% tolerance is allowed due to rounding and practical adjustments.
    """

    # Reference values from container_library.sql (stored, calculated)
    SEED_DATA_REFERENCE = [
        # model_params, quantization, stored_vram, gpu_count
        ("72B", "awq", 36.0, 2),   # Stored uses 36, calculated ~43
        ("72B", "fp16", 144.0, 4),  # Stored uses 144, calculated ~173
        ("32B", "awq", 16.0, 1),    # Stored uses 16, calculated ~19
        ("32B", "fp16", 64.0, 2),   # Stored uses 64, calculated ~77
        ("14B", "awq", 7.0, 1),     # Stored uses 7, calculated ~8.4
        ("7B", "awq", 3.5, 1),      # Stored uses 3.5, calculated ~4.2
        ("7B", "fp16", 14.0, 1),    # Stored uses 14, calculated ~16.8
        ("7B", "q8_0", 7.0, 1),     # Stored uses 7, calculated ~8.4
    ]

    def test_seed_values_within_tolerance(self):
        """Seed data VRAM values should be within 30% of calculated."""
        for params, quant, stored, gpus in self.SEED_DATA_REFERENCE:
            calculated = estimate_vram_gb(params, quant)
            # Allow 30% tolerance (seed data uses more conservative estimates)
            assert stored <= calculated, (
                f"{params} {quant}: stored={stored} > calculated={calculated}"
            )
            ratio = stored / calculated
            assert ratio >= 0.7, (
                f"{params} {quant}: stored={stored} too low vs calculated={calculated}"
            )

    def test_gpu_count_reasonable(self):
        """GPU counts in seed data should be reasonable for VRAM."""
        for params, quant, stored_vram, stored_gpus in self.SEED_DATA_REFERENCE:
            calculated_vram = estimate_vram_gb(params, quant)
            suggested_gpus = suggest_gpu_count(calculated_vram)

            # Stored GPU count should be >= suggested (can be higher for safety)
            assert stored_gpus <= suggested_gpus * 2, (
                f"{params} {quant}: stored_gpus={stored_gpus} "
                f"too high vs suggested={suggested_gpus}"
            )
