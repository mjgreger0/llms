"""Unit tests for Model Router (Task 7.3)."""

import pytest

from dashboard.backend.services.model_router import parse_model_name, ModelRouter


class TestParseModelName:
    """Test Task 3.2: Model name parsing."""

    def test_parse_awq_quantization(self):
        """Test parsing AWQ quantization suffix."""
        model, quant = parse_model_name("qwen2.5-72b-instruct-awq")
        assert model == "qwen2.5-72b-instruct"
        assert quant == "awq"

    def test_parse_gptq_quantization(self):
        """Test parsing GPTQ quantization suffix."""
        model, quant = parse_model_name("llama3.1-70b-gptq")
        assert model == "llama3.1-70b"
        assert quant == "gptq"

    def test_parse_gguf_quantization(self):
        """Test parsing GGUF quantization suffix (q4_k_m)."""
        model, quant = parse_model_name("mistral-7b-q4_k_m")
        assert model == "mistral-7b"
        assert quant == "q4_k_m"

    def test_parse_q8_0_quantization(self):
        """Test parsing q8_0 quantization suffix."""
        model, quant = parse_model_name("phi-3-mini-q8_0")
        assert model == "phi-3-mini"
        assert quant == "q8_0"

    def test_parse_fp8_quantization(self):
        """Test parsing fp8 quantization suffix."""
        model, quant = parse_model_name("llama-3-8b-fp8")
        assert model == "llama-3-8b"
        assert quant == "fp8"

    def test_parse_fp16_quantization(self):
        """Test parsing fp16 quantization suffix."""
        model, quant = parse_model_name("qwen-7b-fp16")
        assert model == "qwen-7b"
        assert quant == "fp16"

    def test_parse_no_quantization(self):
        """Test parsing model with no quantization suffix."""
        model, quant = parse_model_name("llama3.1-8b-instruct")
        assert model == "llama3.1-8b-instruct"
        assert quant is None

    def test_parse_complex_name_with_quant(self):
        """Test parsing complex model name with quantization."""
        model, quant = parse_model_name("qwen2.5-72b-instruct-v2.1-awq")
        assert model == "qwen2.5-72b-instruct-v2.1"
        assert quant == "awq"

    def test_parse_exl2_quantization(self):
        """Test parsing EXL2 quantization suffix."""
        model, quant = parse_model_name("codellama-34b-exl2")
        assert model == "codellama-34b"
        assert quant == "exl2"

    def test_parse_bnb_quantization(self):
        """Test parsing BNB (bitsandbytes) quantization suffix."""
        model, quant = parse_model_name("falcon-40b-bnb")
        assert model == "falcon-40b"
        assert quant == "bnb"


class TestModelRouterInit:
    """Test Task 3.1: ModelRouter initialization."""

    def test_model_router_instantiation(self):
        """Test ModelRouter can be instantiated."""
        router = ModelRouter()
        assert router._http_client is None
        assert router._lock is not None
        assert router._last_used == {}

    @pytest.mark.asyncio
    async def test_model_router_startup_shutdown(self):
        """Test ModelRouter startup and shutdown."""
        router = ModelRouter()

        await router.startup()
        assert router._http_client is not None

        await router.shutdown()
        # After shutdown, client should be closed


class TestKnownQuantizations:
    """Test that all expected quantization formats are recognized."""

    @pytest.mark.parametrize("quant", [
        "awq", "gptq", "exl2", "gguf", "bnb",
        "fp16", "fp8", "bf16",
        "q4_k_m", "q8_0", "q5_k_m", "q6_k", "q4_0", "q5_0",
    ])
    def test_known_quantization_recognized(self, quant):
        """Test that known quantization suffixes are recognized."""
        model, parsed_quant = parse_model_name(f"test-model-{quant}")
        assert parsed_quant == quant
