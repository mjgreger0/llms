"""Model service - CRUD operations for models and quantizations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from dashboard.backend.models.database import Model, ModelQuantization

class ModelService:
    async def get_all_with_quantizations(self, db: AsyncSession) -> list[Model]:
        result = await db.execute(
            select(Model)
            .options(selectinload(Model.quantizations))
            .order_by(Model.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, model_id: int) -> Optional[Model]:
        result = await db.execute(
            select(Model)
            .options(selectinload(Model.quantizations))
            .where(Model.id == model_id)
        )
        return result.scalar_one_or_none()

model_service = ModelService()
