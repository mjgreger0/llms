"""Machine service - CRUD operations for machines."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from dashboard.backend.models.database import Machine

class MachineService:
    async def get_all(self, db: AsyncSession) -> list[Machine]:
        result = await db.execute(select(Machine).order_by(Machine.hostname))
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, machine_id: str) -> Optional[Machine]:
        result = await db.execute(select(Machine).where(Machine.id == machine_id))
        return result.scalar_one_or_none()

machine_service = MachineService()
