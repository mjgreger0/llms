"""Control API endpoints for the LLM Serve Dashboard.

Provides CRUD operations for managing machines, models, container configurations,
settings, and viewing cluster status. These endpoints form the core of the
dashboard's control plane.
"""

from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from dashboard.backend.db.session import get_db
from dashboard.backend.models import schemas
from dashboard.backend.models.database import (
    ContainerConfig,
    Machine,
    Model,
    ModelQuantization,
    Setting,
)

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Create router with control tag and /api prefix
router = APIRouter(prefix="/api", tags=["control"])


# ============================================================================
# Cluster Status Endpoints
# ============================================================================


@router.get("/cluster/status", response_model=schemas.ClusterStatusResponse)
async def get_cluster_status(
    db: AsyncSession = Depends(get_db),
) -> schemas.ClusterStatusResponse:
    """Get cluster-wide status overview.

    Returns high-level metrics about the cluster including machine counts,
    GPU availability, and running models. This provides a dashboard overview.

    Args:
        db: Database session dependency

    Returns:
        ClusterStatusResponse with cluster metrics

    Note:
        Currently returns placeholder/mock data. Will be implemented with
        real cluster state tracking in Phase 2.
    """
    logger.info("cluster_status_requested")

    # TODO: Implement real cluster status aggregation
    # For now, return mock data
    return schemas.ClusterStatusResponse(
        total_machines=0,
        online_machines=0,
        total_gpus=0,
        free_gpus=0,
        running_models=[],
    )


# ============================================================================
# Machine Endpoints
# ============================================================================


@router.get("/machines", response_model=List[schemas.MachineListItem])
async def list_machines(
    db: AsyncSession = Depends(get_db),
) -> List[schemas.MachineListItem]:
    """List all machines in the cluster.

    Returns a summary view of all registered machines with their current status.

    Args:
        db: Database session dependency

    Returns:
        List of MachineListItem objects
    """
    logger.info("machines_list_requested")

    # Query all machines
    result = await db.execute(select(Machine).order_by(Machine.hostname))
    machines = result.scalars().all()

    # Convert to list items with computed status
    machine_list = []
    for machine in machines:
        # Compute status based on last_seen
        # If last_seen is within 5 minutes, consider online
        # TODO: Make this configurable via settings
        if machine.last_seen:
            time_diff = datetime.now(machine.last_seen.tzinfo) - machine.last_seen
            machine_status = "online" if time_diff.total_seconds() < 300 else "offline"
        else:
            machine_status = "never_seen"

        machine_list.append(
            schemas.MachineListItem(
                id=machine.id,
                hostname=machine.hostname,
                ip_address=machine.ip_address or "",
                status=machine_status,
                cpu_cores=machine.cpu_cores,
                memory_gb=machine.memory_gb,
                last_seen=machine.last_seen or machine.first_seen,
            )
        )

    logger.info("machines_list_returned", count=len(machine_list))
    return machine_list


@router.get("/machines/{machine_id}", response_model=schemas.MachineResponse)
async def get_machine(
    machine_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.MachineResponse:
    """Get detailed information about a specific machine.

    Args:
        machine_id: Unique machine identifier
        db: Database session dependency

    Returns:
        MachineResponse with full machine details

    Raises:
        HTTPException: 404 if machine not found
    """
    logger.info("machine_details_requested", machine_id=machine_id)

    # Query machine by ID
    result = await db.execute(select(Machine).where(Machine.id == machine_id))
    machine = result.scalar_one_or_none()

    if not machine:
        logger.warning("machine_not_found", machine_id=machine_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id '{machine_id}' not found",
        )

    # Compute status
    if machine.last_seen:
        time_diff = datetime.now(machine.last_seen.tzinfo) - machine.last_seen
        machine_status = "online" if time_diff.total_seconds() < 300 else "offline"
    else:
        machine_status = "never_seen"

    logger.info("machine_details_returned", machine_id=machine_id)
    return schemas.MachineResponse(
        id=machine.id,
        hostname=machine.hostname,
        ip_address=machine.ip_address or "",
        notes=machine.notes,
        first_seen=machine.first_seen,
        last_seen=machine.last_seen or machine.first_seen,
        cpu_model=machine.cpu_model,
        cpu_cores=machine.cpu_cores,
        memory_gb=machine.memory_gb,
        status=machine_status,
    )


# ============================================================================
# Model Endpoints
# ============================================================================


@router.get("/models", response_model=List[schemas.ModelResponse])
async def list_models(
    db: AsyncSession = Depends(get_db),
) -> List[schemas.ModelResponse]:
    """List all models with their quantizations.

    Uses eager loading to efficiently fetch models with nested quantization data.

    Args:
        db: Database session dependency

    Returns:
        List of ModelResponse objects with nested quantizations
    """
    logger.info("models_list_requested")

    # Query all models with eager loading of quantizations
    result = await db.execute(
        select(Model)
        .options(selectinload(Model.quantizations))
        .order_by(Model.name)
    )
    models = result.scalars().all()

    # Convert to response models
    model_responses = []
    for model in models:
        quantization_responses = [
            schemas.QuantizationResponse(
                id=quant.id,
                model_id=quant.model_id,
                quantization=quant.quantization,
                file_path=quant.file_path or "",
                file_size_gb=quant.file_size_gb,
                vram_required_gb=quant.vram_required_gb,
                gpu_count=quant.gpu_count,
                added_at=quant.added_at,
            )
            for quant in model.quantizations
        ]

        model_responses.append(
            schemas.ModelResponse(
                id=model.id,
                name=model.name,
                provider=model.provider or "",
                huggingface_id=model.huggingface_id,
                base_parameters=model.base_parameters,
                added_at=model.added_at,
                quantizations=quantization_responses,
            )
        )

    logger.info("models_list_returned", count=len(model_responses))
    return model_responses


# ============================================================================
# Container Config Endpoints
# ============================================================================


@router.get("/containers", response_model=List[schemas.ContainerConfigResponse])
async def list_container_configs(
    db: AsyncSession = Depends(get_db),
) -> List[schemas.ContainerConfigResponse]:
    """List all container configurations.

    Returns container configurations with nested model quantization information.

    Args:
        db: Database session dependency

    Returns:
        List of ContainerConfigResponse objects
    """
    logger.info("container_configs_list_requested")

    # Query all container configs with eager loading of model quantization
    result = await db.execute(
        select(ContainerConfig)
        .options(
            selectinload(ContainerConfig.model_quantization).selectinload(
                ModelQuantization.model
            )
        )
        .order_by(ContainerConfig.id)
    )
    configs = result.scalars().all()

    # Convert to response models
    config_responses = []
    for config in configs:
        # Build ModelQuantInfo if available
        model_quant_info = None
        if config.model_quantization:
            quant = config.model_quantization
            model_quant_info = schemas.ModelQuantInfo(
                id=quant.id,
                model_name=quant.model.name if quant.model else "Unknown",
                quantization=quant.quantization,
                file_path=quant.file_path or "",
            )

        config_responses.append(
            schemas.ContainerConfigResponse(
                id=config.id,
                model_quant_id=config.model_quant_id,
                runtime=config.runtime,
                context_length=config.context_length,
                max_parallel=config.max_parallel,
                tensor_parallel=config.tensor_parallel,
                pipeline_parallel=config.pipeline_parallel,
                extra_args=config.extra_args,
                created_at=config.created_at,
                updated_at=config.updated_at,
                model_quant=model_quant_info,
            )
        )

    logger.info("container_configs_list_returned", count=len(config_responses))
    return config_responses


@router.get("/containers/{config_id}", response_model=schemas.ContainerConfigResponse)
async def get_container_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
) -> schemas.ContainerConfigResponse:
    """Get detailed information about a specific container configuration.

    Args:
        config_id: Container configuration ID
        db: Database session dependency

    Returns:
        ContainerConfigResponse with full config details

    Raises:
        HTTPException: 404 if config not found
    """
    logger.info("container_config_details_requested", config_id=config_id)

    # Query config by ID with eager loading
    result = await db.execute(
        select(ContainerConfig)
        .where(ContainerConfig.id == config_id)
        .options(
            selectinload(ContainerConfig.model_quantization).selectinload(
                ModelQuantization.model
            )
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        logger.warning("container_config_not_found", config_id=config_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container config with id {config_id} not found",
        )

    # Build ModelQuantInfo if available
    model_quant_info = None
    if config.model_quantization:
        quant = config.model_quantization
        model_quant_info = schemas.ModelQuantInfo(
            id=quant.id,
            model_name=quant.model.name if quant.model else "Unknown",
            quantization=quant.quantization,
            file_path=quant.file_path or "",
        )

    logger.info("container_config_details_returned", config_id=config_id)
    return schemas.ContainerConfigResponse(
        id=config.id,
        model_quant_id=config.model_quant_id,
        runtime=config.runtime,
        context_length=config.context_length,
        max_parallel=config.max_parallel,
        tensor_parallel=config.tensor_parallel,
        pipeline_parallel=config.pipeline_parallel,
        extra_args=config.extra_args,
        created_at=config.created_at,
        updated_at=config.updated_at,
        model_quant=model_quant_info,
    )


# ============================================================================
# Logs Endpoint (Placeholder)
# ============================================================================


@router.get("/logs", response_model=schemas.LogsResponse)
async def get_logs(
    level: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> schemas.LogsResponse:
    """Get system logs with optional filtering.

    Args:
        level: Filter by log level (debug, info, warning, error)
        limit: Maximum number of log entries to return (default: 100)
        offset: Number of entries to skip (default: 0)
        db: Database session dependency

    Returns:
        LogsResponse with log entries and total count

    Note:
        Currently returns placeholder data. Will be implemented with
        structured log storage in a future phase.
    """
    logger.info(
        "logs_requested",
        level=level,
        limit=limit,
        offset=offset,
    )

    # TODO: Implement real log querying from database or log aggregation system
    # For now, return placeholder data
    placeholder_entries = [
        schemas.LogEntry(
            timestamp=datetime.now(),
            level="info",
            event="dashboard_started",
            context={"version": "1.0.0"},
        ),
        schemas.LogEntry(
            timestamp=datetime.now(),
            level="info",
            event="placeholder_log_entry",
            context={"message": "Log storage not yet implemented"},
        ),
    ]

    return schemas.LogsResponse(
        entries=placeholder_entries,
        total_count=len(placeholder_entries),
    )


# ============================================================================
# Settings Endpoints
# ============================================================================


@router.get("/settings", response_model=Dict[str, any])
async def list_settings(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, any]:
    """Get all system settings as a dictionary.

    Returns all settings as key-value pairs for easy access.

    Args:
        db: Database session dependency

    Returns:
        Dictionary mapping setting keys to their values
    """
    logger.info("settings_list_requested")

    # Query all settings
    result = await db.execute(select(Setting).order_by(Setting.key))
    settings = result.scalars().all()

    # Convert to dictionary
    settings_dict = {setting.key: setting.value for setting in settings}

    logger.info("settings_list_returned", count=len(settings_dict))
    return settings_dict


@router.get("/settings/{key}", response_model=schemas.SettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.SettingResponse:
    """Get a specific setting by key.

    Args:
        key: Setting key name
        db: Database session dependency

    Returns:
        SettingResponse with key, value, and timestamp

    Raises:
        HTTPException: 404 if setting not found
    """
    logger.info("setting_requested", key=key)

    # Query setting by key
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        logger.warning("setting_not_found", key=key)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting with key '{key}' not found",
        )

    logger.info("setting_returned", key=key)
    return schemas.SettingResponse(
        key=setting.key,
        value=setting.value,
        updated_at=setting.updated_at,
    )


@router.put("/settings/{key}", response_model=schemas.SettingResponse)
async def update_setting(
    key: str,
    update: schemas.SettingUpdate,
    db: AsyncSession = Depends(get_db),
) -> schemas.SettingResponse:
    """Update or create a setting.

    Updates an existing setting or creates a new one if it doesn't exist.

    Args:
        key: Setting key name
        update: SettingUpdate with new value
        db: Database session dependency

    Returns:
        SettingResponse with updated setting

    Note:
        The updated_at timestamp is automatically updated by the database.
    """
    logger.info("setting_update_requested", key=key)

    # Try to find existing setting
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        # Update existing setting
        setting.value = update.value
        logger.info("setting_updated", key=key)
    else:
        # Create new setting
        setting = Setting(key=key, value=update.value)
        db.add(setting)
        logger.info("setting_created", key=key)

    await db.commit()
    await db.refresh(setting)

    return schemas.SettingResponse(
        key=setting.key,
        value=setting.value,
        updated_at=setting.updated_at,
    )
