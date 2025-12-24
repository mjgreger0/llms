"""Initial database tables

Revision ID: 001
Revises:
Create Date: 2025-12-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create machines table
    op.create_table(
        'machines',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('hostname', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cpu_model', sa.String(255), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('memory_gb', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    # Create models table
    op.create_table(
        'models',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('provider', sa.String(255), nullable=True),
        sa.Column('huggingface_id', sa.String(512), nullable=True),
        sa.Column('base_parameters', sa.String(50), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create model_quantizations table
    op.create_table(
        'model_quantizations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('quantization', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=True),
        sa.Column('file_size_gb', sa.Float(), nullable=True),
        sa.Column('vram_required_gb', sa.Float(), nullable=True),
        sa.Column('gpu_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('model_id', 'quantization', name='uq_model_quantization'),
        sa.CheckConstraint('gpu_count >= 1', name='ck_gpu_count_positive'),
    )

    # Create container_configs table
    op.create_table(
        'container_configs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('model_quant_id', sa.Integer(), nullable=False),
        sa.Column('runtime', sa.String(50), nullable=False, server_default='vllm'),
        sa.Column('context_length', sa.Integer(), nullable=False, server_default='8192'),
        sa.Column('max_parallel', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('tensor_parallel', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('pipeline_parallel', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('extra_args', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['model_quant_id'], ['model_quantizations.id'], ondelete='CASCADE'),
    )

    # Create credentials table
    op.create_table(
        'credentials',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create settings table
    op.create_table(
        'settings',
        sa.Column('key', sa.String(255), primary_key=True),
        sa.Column('value', JSONB, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('settings')
    op.drop_table('credentials')
    op.drop_table('container_configs')
    op.drop_table('model_quantizations')
    op.drop_table('models')
    op.drop_table('machines')
