"""Settings service - CRUD operations for key-value settings."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Any
from dashboard.backend.models.database import Setting

class SettingsService:
    async def get_all(self, db: AsyncSession) -> dict[str, Any]:
        result = await db.execute(select(Setting))
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}

    async def get_by_key(self, db: AsyncSession, key: str) -> Optional[Setting]:
        result = await db.execute(select(Setting).where(Setting.key == key))
        return result.scalar_one_or_none()

    async def set_value(self, db: AsyncSession, key: str, value: Any) -> Setting:
        setting = await self.get_by_key(db, key)
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.add(setting)
        await db.commit()
        await db.refresh(setting)
        return setting

settings_service = SettingsService()
