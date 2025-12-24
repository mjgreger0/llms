"""TimescaleDB hypertables for time-series data

Revision ID: 002
Revises: 001
Create Date: 2025-12-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # Create cpu_stats table
    op.create_table(
        'cpu_stats',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('machine_id', sa.String(255), nullable=False),
        sa.Column('cores', sa.Integer(), nullable=True),
        sa.Column('load_percent', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('time', 'machine_id'),
    )

    # Convert cpu_stats to hypertable
    op.execute("SELECT create_hypertable('cpu_stats', 'time', if_not_exists => TRUE);")

    # Add retention policy for cpu_stats (30 days)
    op.execute("SELECT add_retention_policy('cpu_stats', INTERVAL '30 days', if_not_exists => TRUE);")

    # Create gpu_stats table
    op.create_table(
        'gpu_stats',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('machine_id', sa.String(255), nullable=False),
        sa.Column('gpu_uuid', sa.String(255), nullable=False),
        sa.Column('gpu_index', sa.Integer(), nullable=True),
        sa.Column('gpu_name', sa.String(255), nullable=True),
        sa.Column('memory_total_gb', sa.Float(), nullable=True),
        sa.Column('memory_used_gb', sa.Float(), nullable=True),
        sa.Column('utilization', sa.Integer(), nullable=True),
        sa.Column('temperature_c', sa.Integer(), nullable=True),
        sa.Column('model_loaded', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('time', 'machine_id', 'gpu_uuid'),
    )

    # Convert gpu_stats to hypertable
    op.execute("SELECT create_hypertable('gpu_stats', 'time', if_not_exists => TRUE);")

    # Add retention policy for gpu_stats (30 days)
    op.execute("SELECT add_retention_policy('gpu_stats', INTERVAL '30 days', if_not_exists => TRUE);")

    # Create memory_stats table
    op.create_table(
        'memory_stats',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('machine_id', sa.String(255), nullable=False),
        sa.Column('total_gb', sa.Float(), nullable=True),
        sa.Column('used_gb', sa.Float(), nullable=True),
        sa.Column('available_gb', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('time', 'machine_id'),
    )

    # Convert memory_stats to hypertable
    op.execute("SELECT create_hypertable('memory_stats', 'time', if_not_exists => TRUE);")

    # Add retention policy for memory_stats (30 days)
    op.execute("SELECT add_retention_policy('memory_stats', INTERVAL '30 days', if_not_exists => TRUE);")


def downgrade() -> None:
    # Drop tables (hypertables are automatically cleaned up)
    op.drop_table('memory_stats')
    op.drop_table('gpu_stats')
    op.drop_table('cpu_stats')

    # Note: We don't drop the TimescaleDB extension as it might be used by other databases
    # If you need to drop it, uncomment the following line:
    # op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")
