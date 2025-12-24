"""Database session management for LLM Serve Dashboard.

Provides async SQLAlchemy session configuration with connection pooling
and FastAPI dependency injection for database access.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dashboard.backend.config import get_settings


# Global engine instance
engine: AsyncEngine | None = None

# Session factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_db() -> None:
    """Initialize database engine and session factory.

    This should be called during application startup.
    Creates the async engine with connection pooling configured
    from application settings.
    """
    global engine, AsyncSessionLocal

    settings = get_settings()

    # Create async engine with asyncpg driver
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.log_level == "DEBUG",  # Log SQL queries in debug mode
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Allow access to objects after commit
        autocommit=False,
        autoflush=False,
    )


async def close_db() -> None:
    """Close database engine and cleanup connections.

    This should be called during application shutdown.
    """
    global engine

    if engine is not None:
        await engine.dispose()
        engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session.

    Yields an async database session that is automatically closed
    after the request completes. Handles exceptions and ensures
    proper cleanup.

    Example:
        ```python
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession

        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```

    Yields:
        AsyncSession: Database session for the request

    Raises:
        RuntimeError: If database has not been initialized
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() during application startup."
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
