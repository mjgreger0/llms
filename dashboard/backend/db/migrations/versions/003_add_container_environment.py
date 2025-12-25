"""Add environment field to container_configs table

Revision ID: 003
Revises: 002
Create Date: 2025-12-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add environment column for container environment variables
    op.add_column(
        'container_configs',
        sa.Column(
            'environment',
            JSONB,
            nullable=True,
            comment='Container environment variables as key-value pairs'
        )
    )

    # Add is_default column to mark default config per model+quant
    op.add_column(
        'container_configs',
        sa.Column(
            'is_default',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='Whether this is the default config for the model+quant'
        )
    )

    # Create trigger function to auto-update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply trigger to container_configs table
    op.execute("""
        CREATE TRIGGER trigger_container_configs_updated_at
        BEFORE UPDATE ON container_configs
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_container_configs_updated_at ON container_configs;")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Remove columns
    op.drop_column('container_configs', 'is_default')
    op.drop_column('container_configs', 'environment')
