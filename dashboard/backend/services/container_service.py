"""Container service - CRUD operations for container configs.

TODO: Phase 4+ - Add container lifecycle management.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from dashboard.backend.models.database import ContainerConfig, ModelQuantization

class ContainerService:
    async def get_all(self, db: AsyncSession) -> list[ContainerConfig]:
        result = await db.execute(
            select(ContainerConfig)
            .options(selectinload(ContainerConfig.model_quantization))
        )
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, config_id: int) -> Optional[ContainerConfig]:
        result = await db.execute(
            select(ContainerConfig)
            .options(selectinload(ContainerConfig.model_quantization))
            .where(ContainerConfig.id == config_id)
        )
        return result.scalar_one_or_none()

container_service = ContainerService()
