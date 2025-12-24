"""Stats storage service for persisting daemon stats to TimescaleDB.

Handles storing CPU, GPU, and memory statistics from daemon reports
into the TimescaleDB hypertables.
"""

from datetime import datetime
from typing import Any, Dict

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.backend.db.session import get_db
from dashboard.backend.models.database import CPUStat, GPUStat, Machine, MemoryStat

logger = structlog.get_logger(__name__)


class StatsStorage:
    """Service for storing daemon statistics to TimescaleDB."""

    async def store_stats(
        self,
        machine_id: str,
        stats: Dict[str, Any],
    ) -> None:
        """Store stats report from a daemon.

        Args:
            machine_id: Machine identifier
            stats: Stats dictionary from daemon report
        """
        try:
            # Get database session
            async for db in get_db():
                await self._store_stats_with_db(db, machine_id, stats)
                break  # Only need one iteration

        except Exception as e:
            logger.error(
                "stats_storage_failed",
                machine_id=machine_id,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _store_stats_with_db(
        self,
        db: AsyncSession,
        machine_id: str,
        stats: Dict[str, Any],
    ) -> None:
        """Store stats with provided database session.

        Args:
            db: Database session
            machine_id: Machine identifier
            stats: Stats dictionary from daemon report
        """
        timestamp = datetime.now()

        # Update machine last_seen
        await self._update_machine(db, machine_id, stats, timestamp)

        # Store CPU stats
        if "cpu" in stats:
            await self._store_cpu_stats(db, machine_id, stats["cpu"], timestamp)

        # Store memory stats
        if "memory" in stats:
            await self._store_memory_stats(db, machine_id, stats["memory"], timestamp)

        # Store GPU stats
        if "gpus" in stats:
            await self._store_gpu_stats(db, machine_id, stats["gpus"], timestamp)

        await db.commit()

        logger.debug(
            "stats_stored",
            machine_id=machine_id,
            timestamp=timestamp.isoformat(),
        )

    async def _update_machine(
        self,
        db: AsyncSession,
        machine_id: str,
        stats: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Update machine record with latest stats.

        Args:
            db: Database session
            machine_id: Machine identifier
            stats: Stats dictionary
            timestamp: Current timestamp
        """
        # Extract hostname and IP if available
        hostname = stats.get("hostname")
        ip_address = stats.get("ip_address")

        # Upsert machine record
        stmt = insert(Machine).values(
            id=machine_id,
            hostname=hostname or machine_id,
            ip_address=ip_address,
            last_seen=timestamp,
            cpu_model=stats.get("cpu", {}).get("model"),
            cpu_cores=stats.get("cpu", {}).get("cores"),
            memory_gb=stats.get("memory", {}).get("total_gb"),
        )

        # On conflict, update last_seen and stats
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "last_seen": timestamp,
                "ip_address": ip_address,
                "cpu_model": stats.get("cpu", {}).get("model"),
                "cpu_cores": stats.get("cpu", {}).get("cores"),
                "memory_gb": stats.get("memory", {}).get("total_gb"),
            },
        )

        await db.execute(stmt)

    async def _store_cpu_stats(
        self,
        db: AsyncSession,
        machine_id: str,
        cpu: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Store CPU statistics.

        Args:
            db: Database session
            machine_id: Machine identifier
            cpu: CPU stats dictionary
            timestamp: Timestamp for the stats
        """
        cpu_stat = CPUStat(
            time=timestamp,
            machine_id=machine_id,
            cores=cpu.get("cores", 0),
            load_percent=cpu.get("load_percent", 0.0),
        )
        db.add(cpu_stat)

    async def _store_memory_stats(
        self,
        db: AsyncSession,
        machine_id: str,
        memory: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Store memory statistics.

        Args:
            db: Database session
            machine_id: Machine identifier
            memory: Memory stats dictionary
            timestamp: Timestamp for the stats
        """
        memory_stat = MemoryStat(
            time=timestamp,
            machine_id=machine_id,
            total_gb=memory.get("total_gb", 0.0),
            used_gb=memory.get("used_gb", 0.0),
            available_gb=memory.get("available_gb", 0.0),
        )
        db.add(memory_stat)

    async def _store_gpu_stats(
        self,
        db: AsyncSession,
        machine_id: str,
        gpus: list[Dict[str, Any]],
        timestamp: datetime,
    ) -> None:
        """Store GPU statistics for all GPUs.

        Args:
            db: Database session
            machine_id: Machine identifier
            gpus: List of GPU stats dictionaries
            timestamp: Timestamp for the stats
        """
        for gpu in gpus:
            gpu_stat = GPUStat(
                time=timestamp,
                machine_id=machine_id,
                gpu_index=gpu.get("index", 0),
                gpu_name=gpu.get("name", "Unknown"),
                gpu_uuid=gpu.get("uuid", "unknown"),
                temperature_c=gpu.get("temperature_c"),
                utilization=gpu.get("utilization"),
                memory_total_gb=gpu.get("memory_total_gb"),
                memory_used_gb=gpu.get("memory_used_gb"),
                model_loaded=gpu.get("model_loaded"),
            )
            db.add(gpu_stat)


# Singleton instance
stats_storage = StatsStorage()
