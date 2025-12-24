#!/usr/bin/env python3
"""Database initialization script for LLM Serve Dashboard.

This script:
1. Creates the database if it doesn't exist
2. Runs all Alembic migrations
3. Seeds initial settings (optional)

Can be run idempotently - safe to run multiple times.

Usage:
    python -m dashboard.backend.scripts.init_db

    # Or with environment variables:
    DATABASE_URL=postgresql+asyncpg://... python -m dashboard.backend.scripts.init_db
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import structlog

# Configure basic logging for script
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ]
)
logger = structlog.get_logger()


async def create_database_if_not_exists(db_url: str) -> bool:
    """Create the database if it doesn't exist.

    Returns True if database was created, False if it already existed.
    """
    # Parse database URL to get connection info
    # postgresql+asyncpg://user:pass@host:port/dbname
    url_parts = db_url.replace("postgresql+asyncpg://", "")

    # Split credentials and host
    if "@" in url_parts:
        creds, host_db = url_parts.split("@", 1)
        if ":" in creds:
            user, password = creds.split(":", 1)
        else:
            user = creds
            password = ""
    else:
        user = "postgres"
        password = ""
        host_db = url_parts

    # Split host:port and database
    if "/" in host_db:
        host_port, db_name = host_db.rsplit("/", 1)
    else:
        host_port = host_db
        db_name = "llmserve"

    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 5432

    logger.info("checking_database", host=host, port=port, database=db_name)

    try:
        # Connect to postgres database to check/create target database
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres",
        )

        try:
            # Check if database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                db_name
            )

            if not exists:
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info("database_created", database=db_name)
                return True
            else:
                logger.info("database_exists", database=db_name)
                return False
        finally:
            await conn.close()
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise


def run_migrations() -> None:
    """Run Alembic migrations to latest version."""
    migrations_dir = Path(__file__).parent.parent / "db" / "migrations"

    logger.info("running_migrations", directory=str(migrations_dir))

    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(migrations_dir),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(
                "migration_failed",
                stdout=result.stdout,
                stderr=result.stderr,
            )
            raise RuntimeError(f"Migration failed: {result.stderr}")

        logger.info("migrations_complete", output=result.stdout.strip())
    except FileNotFoundError:
        logger.warning("alembic_not_found", message="Alembic not installed or not in PATH")
        raise


async def seed_initial_settings(db_url: str) -> None:
    """Seed initial settings if they don't exist."""
    # Parse connection info
    url_parts = db_url.replace("postgresql+asyncpg://", "")

    if "@" in url_parts:
        creds, host_db = url_parts.split("@", 1)
        if ":" in creds:
            user, password = creds.split(":", 1)
        else:
            user = creds
            password = ""
    else:
        user = "postgres"
        password = ""
        host_db = url_parts

    if "/" in host_db:
        host_port, db_name = host_db.rsplit("/", 1)
    else:
        host_port = host_db
        db_name = "llmserve"

    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 5432

    logger.info("seeding_settings")

    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name,
        )

        try:
            # Check if settings table exists
            table_exists = await conn.fetchval(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'settings'"
            )

            if not table_exists:
                logger.info("settings_table_not_found", message="Run migrations first")
                return

            # Default settings to seed
            default_settings = {
                "metrics_retention_days": 30,
                "health_check_interval_seconds": 1,
                "default_runtime": "vllm",
            }

            for key, value in default_settings.items():
                # Insert if not exists
                await conn.execute(
                    '''
                    INSERT INTO settings (key, value, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (key) DO NOTHING
                    ''',
                    key,
                    {"value": value},
                )

            logger.info("settings_seeded", count=len(default_settings))
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("seed_settings_failed", error=str(e))


async def main() -> int:
    """Main entry point for database initialization."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://llmserve:llmserve@localhost:5432/llmserve"
    )

    logger.info("init_db_starting", database_url=db_url.split("@")[-1])

    try:
        # Step 1: Create database if needed
        await create_database_if_not_exists(db_url)

        # Step 2: Run migrations
        run_migrations()

        # Step 3: Seed initial settings
        await seed_initial_settings(db_url)

        logger.info("init_db_complete")
        return 0
    except Exception as e:
        logger.error("init_db_failed", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
