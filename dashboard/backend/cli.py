"""
CLI tools for LLM Serve Dashboard administration.

This module provides command-line utilities for database management,
seed data loading, and other administrative tasks.

Usage:
    python -m dashboard.backend.cli seed-container-library
    python -m dashboard.backend.cli --help
"""

import argparse
import asyncio
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


async def seed_container_library(force: bool = False) -> int:
    """
    Load container library seed data into the database.

    Args:
        force: If True, reload seed data even if tables have data

    Returns:
        Exit code (0 for success, 1 for error)
    """
    from sqlalchemy import text

    from dashboard.backend.db.session import AsyncSessionLocal, init_db

    # Initialize database connection
    await init_db()

    if AsyncSessionLocal is None:
        logger.error("database_not_initialized")
        return 1

    # Find seed data file
    script_dir = Path(__file__).parent
    seed_file = script_dir / "db" / "seed_data" / "container_library.sql"

    if not seed_file.exists():
        logger.error(
            "seed_file_not_found",
            path=str(seed_file),
        )
        print(f"Error: Seed file not found: {seed_file}")
        return 1

    async with AsyncSessionLocal() as session:
        try:
            # Check if seed data already exists (unless force flag is set)
            if not force:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM models")
                )
                count = result.scalar()

                if count and count > 0:
                    logger.info(
                        "seed_data_already_exists",
                        model_count=count,
                    )
                    print(f"Seed data already exists ({count} models). Use --force to reload.")
                    return 0

            # Read and execute seed SQL
            sql_content = seed_file.read_text()

            logger.info(
                "loading_seed_data",
                file=str(seed_file),
            )
            print(f"Loading seed data from: {seed_file}")

            # Execute the SQL
            # Split by statement to handle multiple statements
            await session.execute(text(sql_content))
            await session.commit()

            # Verify the load
            model_result = await session.execute(text("SELECT COUNT(*) FROM models"))
            model_count = model_result.scalar()

            quant_result = await session.execute(
                text("SELECT COUNT(*) FROM model_quantizations")
            )
            quant_count = quant_result.scalar()

            config_result = await session.execute(
                text("SELECT COUNT(*) FROM container_configs")
            )
            config_count = config_result.scalar()

            logger.info(
                "seed_data_loaded",
                models=model_count,
                quantizations=quant_count,
                configs=config_count,
            )
            print(f"Successfully loaded seed data:")
            print(f"  - {model_count} models")
            print(f"  - {quant_count} quantizations")
            print(f"  - {config_count} container configs")

            return 0

        except Exception as e:
            logger.error(
                "seed_data_load_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            print(f"Error loading seed data: {e}")
            await session.rollback()
            return 1


async def list_models() -> int:
    """
    List all models and their quantizations in the database.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    from sqlalchemy import text

    from dashboard.backend.db.session import AsyncSessionLocal, init_db

    # Initialize database connection
    await init_db()

    if AsyncSessionLocal is None:
        logger.error("database_not_initialized")
        return 1

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                text("""
                    SELECT
                        m.name,
                        m.provider,
                        m.base_parameters,
                        mq.quantization,
                        mq.vram_required_gb,
                        mq.gpu_count
                    FROM models m
                    LEFT JOIN model_quantizations mq ON m.id = mq.model_id
                    ORDER BY m.name, mq.quantization
                """)
            )
            rows = result.fetchall()

            if not rows:
                print("No models found in database.")
                return 0

            # Print table header
            print(f"{'Model':<30} {'Provider':<12} {'Params':<8} {'Quant':<10} {'VRAM':<8} {'GPUs':<5}")
            print("-" * 80)

            current_model = None
            for row in rows:
                name, provider, params, quant, vram, gpus = row
                if name != current_model:
                    current_model = name
                    print(f"{name:<30} {provider or '-':<12} {params or '-':<8}", end="")
                else:
                    print(f"{'':<30} {'':<12} {'':<8}", end="")

                if quant:
                    print(f" {quant:<10} {vram or '-':<8} {gpus or '-':<5}")
                else:
                    print(f" {'-':<10} {'-':<8} {'-':<5}")

            return 0

        except Exception as e:
            logger.error(
                "list_models_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            print(f"Error listing models: {e}")
            return 1


async def verify_seed_vram() -> int:
    """
    Verify VRAM estimates in seed data against calculated values.

    Returns:
        Exit code (0 for success, 1 for discrepancies found)
    """
    from sqlalchemy import text

    from dashboard.backend.db.session import AsyncSessionLocal, init_db

    try:
        from dashboard.backend.utils.vram import estimate_vram_gb
    except ImportError:
        print("Error: VRAM utilities not available. Run after Phase 7 is complete.")
        return 1

    # Initialize database connection
    await init_db()

    if AsyncSessionLocal is None:
        logger.error("database_not_initialized")
        return 1

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                text("""
                    SELECT
                        m.name,
                        m.base_parameters,
                        mq.quantization,
                        mq.vram_required_gb
                    FROM models m
                    JOIN model_quantizations mq ON m.id = mq.model_id
                    ORDER BY m.name, mq.quantization
                """)
            )
            rows = result.fetchall()

            if not rows:
                print("No quantizations found in database.")
                return 0

            print(f"{'Model':<30} {'Quant':<10} {'Stored':<10} {'Calculated':<12} {'Diff %':<8}")
            print("-" * 75)

            discrepancies = []

            for row in rows:
                name, params, quant, stored_vram = row

                if not params:
                    print(f"{name:<30} {quant:<10} {stored_vram or '-':<10} {'N/A':<12} {'N/A':<8}")
                    continue

                try:
                    calculated = estimate_vram_gb(params, quant)
                    diff_pct = abs(calculated - stored_vram) / calculated * 100 if calculated else 0

                    status = ""
                    if diff_pct > 10:
                        status = " !"
                        discrepancies.append((name, quant, stored_vram, calculated, diff_pct))

                    print(
                        f"{name:<30} {quant:<10} {stored_vram:<10.1f} {calculated:<12.1f} {diff_pct:<7.1f}%{status}"
                    )
                except ValueError as e:
                    print(f"{name:<30} {quant:<10} {stored_vram or '-':<10} {'Error':<12} {str(e)}")

            if discrepancies:
                print(f"\n{len(discrepancies)} discrepancies found (>10% difference):")
                for name, quant, stored, calc, diff in discrepancies:
                    print(f"  - {name} {quant}: stored={stored:.1f}, calculated={calc:.1f} ({diff:.1f}%)")
                return 1

            print("\nAll VRAM estimates are within 10% of calculated values.")
            return 0

        except Exception as e:
            logger.error(
                "verify_vram_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            print(f"Error verifying VRAM: {e}")
            return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LLM Serve Dashboard CLI tools",
        prog="python -m dashboard.backend.cli",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # seed-container-library command
    seed_parser = subparsers.add_parser(
        "seed-container-library",
        help="Load container library seed data into the database",
    )
    seed_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force reload even if data already exists",
    )

    # list-models command
    subparsers.add_parser(
        "list-models",
        help="List all models and quantizations in the database",
    )

    # verify-vram command
    subparsers.add_parser(
        "verify-vram",
        help="Verify VRAM estimates against calculated values",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    # Run the appropriate command
    if args.command == "seed-container-library":
        return asyncio.run(seed_container_library(force=args.force))
    elif args.command == "list-models":
        return asyncio.run(list_models())
    elif args.command == "verify-vram":
        return asyncio.run(verify_seed_vram())
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
