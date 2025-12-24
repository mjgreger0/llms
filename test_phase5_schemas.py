#!/usr/bin/env python3
"""
Test script for Phase 5 Task 1.1 and 1.2 implementations.

This script validates that the new schema files are properly structured
and can be imported and used correctly.
"""

import sys
from datetime import datetime


def test_openai_schemas():
    """Test Task 1.1: OpenAI-compatible schemas."""
    print("Testing Task 1.1: OpenAI-compatible schemas...")

    from dashboard.backend.models.openai_schemas import (
        ChatCompletionRequest,
        CompletionRequest,
        ChatCompletionResponse,
        CompletionResponse,
        ChatCompletionChunk,
        CompletionChunk,
        Message,
        MessageRole,
        DeltaMessage,
        Choice,
        ChunkChoice,
        TokenUsage,
        ModelInfo,
        ModelList,
        ErrorResponse,
        ErrorDetail,
    )

    # Test ChatCompletionRequest
    req = ChatCompletionRequest(
        model="test-model",
        messages=[
            Message(role=MessageRole.USER, content="Hello!"),
        ],
        stream=True,
        max_tokens=100,
        temperature=0.7,
    )
    assert req.model == "test-model"
    assert len(req.messages) == 1
    assert req.messages[0].content == "Hello!"
    print("  ✓ ChatCompletionRequest")

    # Test ChatCompletionResponse
    response = ChatCompletionResponse(
        id="test-id",
        created=int(datetime.now().timestamp()),
        model="test-model",
        choices=[
            Choice(
                index=0,
                message=Message(role=MessageRole.ASSISTANT, content="Hi there!"),
                finish_reason="stop",
            )
        ],
        usage=TokenUsage(prompt_tokens=5, completion_tokens=3, total_tokens=8),
    )
    assert response.object == "chat.completion"
    print("  ✓ ChatCompletionResponse")

    # Test ChatCompletionChunk
    chunk = ChatCompletionChunk(
        id="test-id",
        created=int(datetime.now().timestamp()),
        model="test-model",
        choices=[
            ChunkChoice(
                index=0,
                delta=DeltaMessage(content="Hello"),
                finish_reason=None,
            )
        ],
    )
    assert chunk.object == "chat.completion.chunk"
    print("  ✓ ChatCompletionChunk")

    # Test CompletionRequest
    comp_req = CompletionRequest(
        model="test-model",
        prompt="Once upon a time",
        max_tokens=50,
    )
    assert comp_req.prompt == "Once upon a time"
    print("  ✓ CompletionRequest")

    # Test ModelList
    model_list = ModelList(
        data=[
            ModelInfo(
                id="model-1",
                created=int(datetime.now().timestamp()),
                owned_by="test-org",
            )
        ]
    )
    assert model_list.object == "list"
    assert len(model_list.data) == 1
    print("  ✓ ModelList and ModelInfo")

    # Test ErrorResponse
    error = ErrorResponse(
        error=ErrorDetail(
            message="Test error",
            type="test_error",
            code="TEST_ERR",
        )
    )
    assert error.error.message == "Test error"
    print("  ✓ ErrorResponse")

    print("✅ Task 1.1 tests passed!\n")


def test_internal_schemas():
    """Test Task 1.2: Internal request/response schemas."""
    print("Testing Task 1.2: Internal request/response schemas...")

    from dashboard.backend.models.internal_schemas import (
        InferenceRequest,
        RequestContext,
        ModelQuant,
        GPURequirement,
        ContainerEndpoint,
    )
    from dashboard.backend.models.openai_schemas import (
        ChatCompletionRequest,
        Message,
        MessageRole,
    )

    # Test InferenceRequest
    chat_req = ChatCompletionRequest(
        model="test-model",
        messages=[Message(role=MessageRole.USER, content="Test")],
    )
    inf_req = InferenceRequest(
        request_id="req-123",
        model="test-model",
        request=chat_req,
        enqueue_time=datetime.now(),
        timeout_seconds=60.0,
        stream=True,
    )
    assert inf_req.request_id == "req-123"
    assert inf_req.timeout_seconds == 60.0
    print("  ✓ InferenceRequest")

    # Test RequestContext
    ctx = RequestContext(
        request_id="req-123",
        error=None,
        result=None,
    )
    assert ctx.request_id == "req-123"
    print("  ✓ RequestContext")

    # Test ModelQuant parsing
    mq1 = ModelQuant.parse("qwen2.5-72b-instruct-awq")
    assert mq1.model_name == "qwen2.5-72b-instruct"
    assert mq1.quantization == "awq"
    print("  ✓ ModelQuant.parse (with AWQ)")

    mq2 = ModelQuant.parse("llama-3-70b-gptq")
    assert mq2.model_name == "llama-3-70b"
    assert mq2.quantization == "gptq"
    print("  ✓ ModelQuant.parse (with GPTQ)")

    mq3 = ModelQuant.parse("mistral-7b-q4_k_m")
    assert mq3.model_name == "mistral-7b"
    assert mq3.quantization == "q4_k_m"
    print("  ✓ ModelQuant.parse (with GGUF quant)")

    mq4 = ModelQuant.parse("qwen2.5-72b-instruct")
    assert mq4.model_name == "qwen2.5-72b-instruct"
    assert mq4.quantization is None
    print("  ✓ ModelQuant.parse (no quantization)")

    # Test GPURequirement
    gpu_req = GPURequirement(
        vram_required_gb=24.0,
        gpu_count=2,
        tensor_parallel=2,
        pipeline_parallel=1,
    )
    assert gpu_req.vram_required_gb == 24.0
    assert gpu_req.gpu_count == 2
    assert not gpu_req.multi_machine
    print("  ✓ GPURequirement")

    # Test multi-machine detection
    gpu_req_multi = GPURequirement(
        vram_required_gb=80.0,
        gpu_count=16,
        tensor_parallel=16,
        pipeline_parallel=1,
    )
    assert gpu_req_multi.multi_machine
    print("  ✓ GPURequirement (multi-machine auto-detection)")

    # Test ContainerEndpoint
    endpoint = ContainerEndpoint(
        machine_id="machine-1",
        host="192.168.1.100",
        port=8000,
        health_url="http://192.168.1.100:8000/health",
    )
    assert endpoint.inference_url == "http://192.168.1.100:8000/v1/chat/completions"
    assert endpoint.completions_url == "http://192.168.1.100:8000/v1/completions"
    assert endpoint.base_url == "http://192.168.1.100:8000"
    print("  ✓ ContainerEndpoint")

    print("✅ Task 1.2 tests passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 5 Tasks 1.1 and 1.2 Validation")
    print("=" * 60 + "\n")

    try:
        test_openai_schemas()
        test_internal_schemas()
        print("=" * 60)
        print("🎉 All tests passed successfully!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
