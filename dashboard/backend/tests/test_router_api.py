"""Integration tests for Router API endpoints (Task 7.4)."""

import pytest
from unittest.mock import AsyncMock, patch

from dashboard.backend.models.openai_schemas import (
    ChatCompletionRequest,
    CompletionRequest,
    Message,
    MessageRole,
)
from dashboard.backend.models.exceptions import (
    ModelNotFoundError,
    InsufficientCapacityError,
    ModelLoadError,
    ContainerTimeoutError,
)


class TestChatCompletionRequest:
    """Test ChatCompletionRequest validation."""

    def test_valid_request(self):
        """Test valid chat completion request."""
        req = ChatCompletionRequest(
            model="test-model",
            messages=[
                Message(role=MessageRole.USER, content="Hello!")
            ],
            stream=True,
            max_tokens=100,
            temperature=0.7,
        )
        assert req.model == "test-model"
        assert len(req.messages) == 1
        assert req.stream is True

    def test_default_stream_value(self):
        """Test default stream value is True."""
        req = ChatCompletionRequest(
            model="test-model",
            messages=[
                Message(role=MessageRole.USER, content="Hello!")
            ],
        )
        assert req.stream is True

    def test_temperature_validation(self):
        """Test temperature must be between 0 and 2."""
        with pytest.raises(ValueError):
            ChatCompletionRequest(
                model="test-model",
                messages=[Message(role=MessageRole.USER, content="Hello!")],
                temperature=2.5,  # Invalid
            )

    def test_max_tokens_positive(self):
        """Test max_tokens must be positive."""
        with pytest.raises(ValueError):
            ChatCompletionRequest(
                model="test-model",
                messages=[Message(role=MessageRole.USER, content="Hello!")],
                max_tokens=-1,  # Invalid
            )


class TestCompletionRequest:
    """Test CompletionRequest validation."""

    def test_valid_request(self):
        """Test valid completion request."""
        req = CompletionRequest(
            model="test-model",
            prompt="Once upon a time",
            max_tokens=100,
        )
        assert req.model == "test-model"
        assert req.prompt == "Once upon a time"

    def test_default_stream_false(self):
        """Test default stream value is False for completions."""
        req = CompletionRequest(
            model="test-model",
            prompt="Test prompt",
        )
        assert req.stream is False


class TestExceptionClasses:
    """Test custom exception classes."""

    def test_model_not_found_error(self):
        """Test ModelNotFoundError."""
        err = ModelNotFoundError(model="test-model", quantization="awq")
        assert err.model == "test-model"
        assert err.quantization == "awq"
        assert "not found" in err.message.lower()

    def test_insufficient_capacity_error(self):
        """Test InsufficientCapacityError."""
        err = InsufficientCapacityError(required_vram=80.0, available_vram=24.0)
        assert err.required_vram == 80.0
        assert err.available_vram == 24.0
        assert "capacity" in err.message.lower() or "vram" in err.message.lower()

    def test_model_load_error(self):
        """Test ModelLoadError."""
        err = ModelLoadError(model="test-model", reason="Container failed")
        assert err.model == "test-model"
        assert err.reason == "Container failed"

    def test_container_timeout_error(self):
        """Test ContainerTimeoutError."""
        err = ContainerTimeoutError(operation="loading", timeout_seconds=120)
        assert err.operation == "loading"
        assert err.timeout_seconds == 120
        assert "timeout" in err.message.lower()


class TestMessageValidation:
    """Test Message model validation."""

    def test_valid_user_message(self):
        """Test valid user message."""
        msg = Message(role=MessageRole.USER, content="Hello!")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello!"

    def test_valid_assistant_message(self):
        """Test valid assistant message."""
        msg = Message(role=MessageRole.ASSISTANT, content="Hi there!")
        assert msg.role == MessageRole.ASSISTANT

    def test_valid_system_message(self):
        """Test valid system message."""
        msg = Message(role=MessageRole.SYSTEM, content="You are a helpful assistant.")
        assert msg.role == MessageRole.SYSTEM

    def test_message_with_name(self):
        """Test message with optional name field."""
        msg = Message(
            role=MessageRole.USER,
            content="Hello!",
            name="user123",
        )
        assert msg.name == "user123"
