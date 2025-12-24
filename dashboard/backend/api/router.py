"""OpenAI-compatible router API endpoints."""

import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from dashboard.backend.db.session import get_db
from dashboard.backend.models.openai_schemas import (
    ChatCompletionRequest,
    CompletionRequest,
    ModelList,
    ModelInfo,
    ErrorResponse,
)
from dashboard.backend.models.database import Model, ModelQuantization
from dashboard.backend.models.exceptions import (
    ModelNotFoundError,
    InsufficientCapacityError,
    ModelLoadError,
    ContainerTimeoutError,
    ContainerNotReadyError,
)
from dashboard.backend.services.model_router import model_router, route_request
from dashboard.backend.services.cluster_state import cluster_state

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["OpenAI API"])


def format_openai_error(message: str, error_type: str, code: Optional[str] = None) -> dict:
    """Format error in OpenAI API format."""
    return {
        "error": {
            "message": message,
            "type": error_type,
            "code": code,
        }
    }


@router.post("/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint.

    Accepts ChatCompletionRequest and returns streaming or non-streaming response.
    Automatically routes requests to available model instances based on capacity.

    Args:
        request: FastAPI request object

    Returns:
        StreamingResponse for streaming requests, dict for non-streaming

    Raises:
        HTTPException: On various error conditions
    """
    request_id = str(uuid.uuid4())

    try:
        body = await request.json()

        logger.info(
            "chat_completion_request",
            request_id=request_id,
            model=body.get("model"),
            stream=body.get("stream", True),
        )

        # Validate request with Pydantic schema
        validated_request = ChatCompletionRequest(**body)

        # Get stream preference
        stream = validated_request.stream

        if stream:
            # Return streaming response
            async def generate():
                async for chunk in route_request(model_router, body, request_id):
                    yield chunk

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-Id": request_id,
                },
            )
        else:
            # Non-streaming response - collect all chunks
            response_content = ""
            async for chunk in route_request(model_router, body, request_id):
                # Parse SSE format
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    try:
                        data = json.loads(chunk[6:].strip())
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                response_content += delta["content"]
                    except json.JSONDecodeError:
                        pass

            return {
                "id": f"chatcmpl-{request_id}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": validated_request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_content
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

    except Exception as e:
        logger.error("chat_completion_error", error=str(e), request_id=request_id)
        raise HTTPException(
            status_code=500,
            detail=format_openai_error(str(e), "server_error")
        )


@router.post("/completions")
async def completions(request: Request):
    """OpenAI-compatible text completions endpoint.

    Accepts CompletionRequest and returns streaming or non-streaming response.
    Automatically routes requests to available model instances based on capacity.

    Args:
        request: FastAPI request object

    Returns:
        StreamingResponse for streaming requests, dict for non-streaming

    Raises:
        HTTPException: On various error conditions
    """
    request_id = str(uuid.uuid4())

    try:
        body = await request.json()

        logger.info(
            "completion_request",
            request_id=request_id,
            model=body.get("model"),
            stream=body.get("stream", False),
        )

        # Validate request with Pydantic schema
        validated_request = CompletionRequest(**body)

        stream = validated_request.stream

        # Convert prompt to messages format for routing
        # Some models may not support /completions directly
        routing_body = {
            "model": validated_request.model,
            "messages": [{"role": "user", "content": validated_request.prompt}],
            "stream": stream,
            "max_tokens": validated_request.max_tokens,
            "temperature": validated_request.temperature,
        }

        if stream:
            async def generate():
                async for chunk in route_request(model_router, routing_body, request_id):
                    yield chunk

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-Id": request_id,
                },
            )
        else:
            # Non-streaming response - collect all chunks
            response_text = ""
            async for chunk in route_request(model_router, routing_body, request_id):
                # Parse SSE format
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    try:
                        data = json.loads(chunk[6:].strip())
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                response_text += delta["content"]
                    except json.JSONDecodeError:
                        pass

            return {
                "id": f"cmpl-{request_id}",
                "object": "text_completion",
                "created": int(time.time()),
                "model": validated_request.model,
                "choices": [
                    {
                        "index": 0,
                        "text": response_text,
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

    except Exception as e:
        logger.error("completion_error", error=str(e), request_id=request_id)
        raise HTTPException(
            status_code=500,
            detail=format_openai_error(str(e), "server_error")
        )


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    """List available models in OpenAI format.

    Returns all model+quantization combinations that are registered in the system.
    Models are identified by combining the base model name with quantization level.

    Returns:
        ModelList: List of available models in OpenAI format
    """
    logger.info("models_list_requested")

    # Query database for all model+quant combinations
    result = await db.execute(
        select(Model, ModelQuantization)
        .join(ModelQuantization, Model.id == ModelQuantization.model_id)
        .order_by(Model.name, ModelQuantization.quantization)
    )
    rows = result.all()

    # Get running models from cluster state
    machines = await cluster_state.get_all_machines()
    running_models = set()
    for machine in machines.values():
        if machine.connected:
            for container in machine.containers:
                if container.status == "ready":
                    running_models.add(container.model)

    # Build model list
    model_data = []
    for model, quant in rows:
        # Build model+quant identifier
        model_id = f"{model.name}-{quant.quantization}" if quant.quantization else model.name

        # Check if running
        is_running = model_id in running_models

        model_data.append({
            "id": model_id,
            "object": "model",
            "created": int(model.added_at.timestamp()) if model.added_at else 0,
            "owned_by": model.provider or "unknown",
            # Extension fields
            "running": is_running,
            "vram_required_gb": quant.vram_required_gb,
            "gpu_count": quant.gpu_count,
        })

    logger.info("models_list_returned", count=len(model_data))
    return {
        "object": "list",
        "data": model_data
    }


@router.get("/models/{model_id:path}")
async def get_model(model_id: str, db: AsyncSession = Depends(get_db)):
    """Get details for a specific model.

    Args:
        model_id: Model identifier (e.g., "llama-3-8b-q4_k_m")

    Returns:
        ModelInfo: Model details in OpenAI format

    Raises:
        HTTPException: 404 if model not found
    """
    logger.info("model_details_requested", model_id=model_id)

    # Parse model_id to extract model name and quantization
    from dashboard.backend.services.model_router import parse_model_name
    model_name, quantization = parse_model_name(model_id)

    # Query database for model details
    stmt = (
        select(Model, ModelQuantization)
        .join(ModelQuantization, Model.id == ModelQuantization.model_id)
        .where(Model.name == model_name)
    )
    if quantization:
        stmt = stmt.where(ModelQuantization.quantization == quantization)

    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=format_openai_error(
                f"Model '{model_id}' not found",
                "not_found",
                "model_not_found"
            )
        )

    model, quant = row

    # Get running status from cluster state
    machines = await cluster_state.get_all_machines()
    is_running = False
    for machine in machines.values():
        if machine.connected:
            for container in machine.containers:
                if container.model == model_id and container.status == "ready":
                    is_running = True
                    break

    return {
        "id": model_id,
        "object": "model",
        "created": int(model.added_at.timestamp()) if model.added_at else 0,
        "owned_by": model.provider or "unknown",
        # Extension fields
        "running": is_running,
        "base_parameters": model.base_parameters,
        "huggingface_id": model.huggingface_id,
        "vram_required_gb": quant.vram_required_gb,
        "gpu_count": quant.gpu_count,
        "file_size_gb": quant.file_size_gb,
    }


# ============================================================================
# Exception Handlers Registration
# ============================================================================

def register_exception_handlers(app):
    """Register exception handlers for router errors.

    These handlers convert router-specific exceptions into OpenAI-compatible
    error responses with appropriate HTTP status codes.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(ModelNotFoundError)
    async def model_not_found_handler(request: Request, exc: ModelNotFoundError):
        """Handle ModelNotFoundError with 404 response."""
        logger.warning(
            "model_not_found",
            model=exc.model,
            quantization=exc.quantization,
        )
        return Response(
            content=json.dumps(format_openai_error(exc.message, "invalid_request_error", exc.code)),
            status_code=404,
            media_type="application/json"
        )

    @app.exception_handler(InsufficientCapacityError)
    async def insufficient_capacity_handler(request: Request, exc: InsufficientCapacityError):
        """Handle InsufficientCapacityError with 503 response."""
        logger.warning(
            "insufficient_capacity",
            required_vram=exc.required_vram,
            available_vram=exc.available_vram,
        )
        return Response(
            content=json.dumps(format_openai_error(exc.message, "server_error", exc.code)),
            status_code=503,
            media_type="application/json",
            headers={"Retry-After": "60"}
        )

    @app.exception_handler(ModelLoadError)
    async def model_load_error_handler(request: Request, exc: ModelLoadError):
        """Handle ModelLoadError with 500 response."""
        logger.error(
            "model_load_error",
            model=exc.model,
            reason=exc.reason,
        )
        return Response(
            content=json.dumps(format_openai_error(exc.message, "server_error", exc.code)),
            status_code=500,
            media_type="application/json"
        )

    @app.exception_handler(ContainerTimeoutError)
    async def container_timeout_handler(request: Request, exc: ContainerTimeoutError):
        """Handle ContainerTimeoutError with 504 response."""
        logger.error(
            "container_timeout",
            operation=exc.operation,
            timeout_seconds=exc.timeout_seconds,
        )
        return Response(
            content=json.dumps(format_openai_error(exc.message, "timeout_error", exc.code)),
            status_code=504,
            media_type="application/json"
        )

    @app.exception_handler(ContainerNotReadyError)
    async def container_not_ready_handler(request: Request, exc: ContainerNotReadyError):
        """Handle ContainerNotReadyError with 503 response."""
        logger.warning(
            "container_not_ready",
            container_id=exc.container_id,
            status=exc.status,
        )
        return Response(
            content=json.dumps(format_openai_error(exc.message, "server_error", exc.code)),
            status_code=503,
            media_type="application/json",
            headers={"Retry-After": "30"}
        )
