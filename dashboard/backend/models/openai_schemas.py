"""
OpenAI-compatible Pydantic schemas for the LLM Serve Dashboard.

This module contains schemas that match the OpenAI API specification for
chat completions, completions, and model listing endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Message Schemas
# ============================================================================

class MessageRole(str, Enum):
    """Valid roles for chat messages."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Message(BaseModel):
    """A single message in a chat conversation.

    Compatible with OpenAI's chat completion message format.
    """
    role: MessageRole = Field(description="The role of the message sender")
    content: str = Field(description="The content of the message")
    name: Optional[str] = Field(None, description="Optional name for function messages")

    model_config = ConfigDict(from_attributes=True)


class DeltaMessage(BaseModel):
    """A delta message for streaming responses.

    Contains partial message updates sent during streaming.
    """
    role: Optional[MessageRole] = Field(None, description="Role of the message (only in first chunk)")
    content: Optional[str] = Field(None, description="Partial content of the message")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request Schemas
# ============================================================================

class ChatCompletionRequest(BaseModel):
    """Request schema for chat completions.

    Compatible with OpenAI's /v1/chat/completions endpoint.
    """
    model: str = Field(description="The model to use for completion")
    messages: List[Message] = Field(description="List of messages in the conversation")
    stream: bool = Field(default=True, description="Whether to stream responses")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Presence penalty")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Frequency penalty")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    n: Optional[int] = Field(1, ge=1, description="Number of completions to generate")
    user: Optional[str] = Field(None, description="Unique user identifier")

    model_config = ConfigDict(from_attributes=True)


class CompletionRequest(BaseModel):
    """Request schema for text completions.

    Compatible with OpenAI's /v1/completions endpoint.
    """
    model: str = Field(description="The model to use for completion")
    prompt: str = Field(description="The prompt to generate from")
    stream: bool = Field(default=True, description="Whether to stream responses")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Presence penalty")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Frequency penalty")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    n: Optional[int] = Field(1, ge=1, description="Number of completions to generate")
    user: Optional[str] = Field(None, description="Unique user identifier")
    suffix: Optional[str] = Field(None, description="Text to append after completion")
    echo: Optional[bool] = Field(False, description="Echo back the prompt")
    logprobs: Optional[int] = Field(None, description="Number of log probabilities to return")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Token Usage Schema
# ============================================================================

class TokenUsage(BaseModel):
    """Token usage statistics for a completion.

    Tracks the number of tokens used in prompt, completion, and total.
    """
    prompt_tokens: int = Field(description="Number of tokens in the prompt")
    completion_tokens: int = Field(description="Number of tokens in the completion")
    total_tokens: int = Field(description="Total number of tokens used")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Choice Schemas (Non-Streaming)
# ============================================================================

class Choice(BaseModel):
    """A single completion choice in a non-streaming response.

    Represents one possible completion from the model.
    """
    index: int = Field(description="Index of this choice in the list")
    message: Message = Field(description="The generated message")
    finish_reason: Optional[str] = Field(None, description="Reason the generation stopped")

    model_config = ConfigDict(from_attributes=True)


class CompletionChoice(BaseModel):
    """A single completion choice for text completions.

    Represents one possible text completion from the model.
    """
    index: int = Field(description="Index of this choice in the list")
    text: str = Field(description="The generated text")
    finish_reason: Optional[str] = Field(None, description="Reason the generation stopped")
    logprobs: Optional[Dict[str, Any]] = Field(None, description="Log probabilities if requested")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Choice Schemas (Streaming)
# ============================================================================

class ChunkChoice(BaseModel):
    """A single choice in a streaming chunk response.

    Represents one delta update during streaming generation.
    """
    index: int = Field(description="Index of this choice in the list")
    delta: DeltaMessage = Field(description="The message delta for this chunk")
    finish_reason: Optional[str] = Field(None, description="Reason the generation stopped (null except final chunk)")

    model_config = ConfigDict(from_attributes=True)


class CompletionChunkChoice(BaseModel):
    """A single choice in a text completion streaming chunk.

    Represents one delta update during streaming text generation.
    """
    index: int = Field(description="Index of this choice in the list")
    text: str = Field(description="The text delta for this chunk")
    finish_reason: Optional[str] = Field(None, description="Reason the generation stopped (null except final chunk)")
    logprobs: Optional[Dict[str, Any]] = Field(None, description="Log probabilities if requested")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas (Non-Streaming)
# ============================================================================

class ChatCompletionResponse(BaseModel):
    """Response schema for non-streaming chat completions.

    Compatible with OpenAI's chat completion response format.
    """
    id: str = Field(description="Unique identifier for this completion")
    object: Literal["chat.completion"] = Field(default="chat.completion", description="Object type")
    created: int = Field(description="Unix timestamp of when the completion was created")
    model: str = Field(description="The model used for completion")
    choices: List[Choice] = Field(description="List of completion choices")
    usage: TokenUsage = Field(description="Token usage statistics")

    model_config = ConfigDict(from_attributes=True)


class CompletionResponse(BaseModel):
    """Response schema for non-streaming text completions.

    Compatible with OpenAI's completion response format.
    """
    id: str = Field(description="Unique identifier for this completion")
    object: Literal["text_completion"] = Field(default="text_completion", description="Object type")
    created: int = Field(description="Unix timestamp of when the completion was created")
    model: str = Field(description="The model used for completion")
    choices: List[CompletionChoice] = Field(description="List of completion choices")
    usage: TokenUsage = Field(description="Token usage statistics")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Response Schemas (Streaming)
# ============================================================================

class ChatCompletionChunk(BaseModel):
    """Response schema for streaming chat completion chunks.

    Each chunk represents a delta update during streaming generation.
    """
    id: str = Field(description="Unique identifier for this completion")
    object: Literal["chat.completion.chunk"] = Field(default="chat.completion.chunk", description="Object type")
    created: int = Field(description="Unix timestamp of when the completion was created")
    model: str = Field(description="The model used for completion")
    choices: List[ChunkChoice] = Field(description="List of delta choices")

    model_config = ConfigDict(from_attributes=True)


class CompletionChunk(BaseModel):
    """Response schema for streaming text completion chunks.

    Each chunk represents a delta update during streaming text generation.
    """
    id: str = Field(description="Unique identifier for this completion")
    object: Literal["text_completion.chunk"] = Field(default="text_completion.chunk", description="Object type")
    created: int = Field(description="Unix timestamp of when the completion was created")
    model: str = Field(description="The model used for completion")
    choices: List[CompletionChunkChoice] = Field(description="List of delta choices")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Model Listing Schemas
# ============================================================================

class ModelInfo(BaseModel):
    """Information about an available model.

    Compatible with OpenAI's model object format.
    """
    id: str = Field(description="Model identifier")
    object: Literal["model"] = Field(default="model", description="Object type")
    created: int = Field(description="Unix timestamp of when the model was created")
    owned_by: str = Field(description="Organization that owns the model")

    model_config = ConfigDict(from_attributes=True)


class ModelList(BaseModel):
    """List of available models.

    Compatible with OpenAI's /v1/models response format.
    """
    object: Literal["list"] = Field(default="list", description="Object type")
    data: List[ModelInfo] = Field(description="List of model objects")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Error Response Schema
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information.

    Contains the error message, type, and optional error code.
    """
    message: str = Field(description="Human-readable error message")
    type: str = Field(description="Error type identifier")
    code: Optional[str] = Field(None, description="Optional error code")

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Error response schema.

    Compatible with OpenAI's error response format.
    """
    error: ErrorDetail = Field(description="Error details")

    model_config = ConfigDict(from_attributes=True)
