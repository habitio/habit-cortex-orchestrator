"""add business_rules table

Revision ID: 7319630d809f
Revises: 90da12bca124
Create Date: 2026-01-27 01:30:27.563553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = '7319630d809f'
down_revision: Union[str, None] = '90da12bca124'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add business_rules table for database-driven validation rules."""
    op.create_table(
        'business_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False, server_default='field_validation'),
        sa.Column('rule_definition', JSON, nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('distributor_id', sa.String(length=255), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_business_rules_id'), 'business_rules', ['id'], unique=False)
    op.create_index(op.f('ix_business_rules_product_id'), 'business_rules', ['product_id'], unique=False)
    op.create_index(op.f('ix_business_rules_rule_type'), 'business_rules', ['rule_type'], unique=False)
    op.create_index(op.f('ix_business_rules_stage'), 'business_rules', ['stage'], unique=False)
    op.create_index(op.f('ix_business_rules_distributor_id'), 'business_rules', ['distributor_id'], unique=False)


def downgrade() -> None:
    """Remove business_rules table."""
    op.drop_index(op.f('ix_business_rules_distributor_id'), table_name='business_rules')
    op.drop_index(op.f('ix_business_rules_stage'), table_name='business_rules')
    op.drop_index(op.f('ix_business_rules_rule_type'), table_name='business_rules')
    op.drop_index(op.f('ix_business_rules_product_id'), table_name='business_rules')
    op.drop_index(op.f('ix_business_rules_id'), table_name='business_rules')
    op.drop_table('business_rules')

