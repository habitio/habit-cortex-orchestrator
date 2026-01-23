"""Add shared_key to products table

Revision ID: fdac636bb28b
Revises: 
Create Date: 2026-01-23 14:36:39.234303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdac636bb28b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add shared_key column to products table
    op.add_column('products', sa.Column('shared_key', sa.String(length=128), nullable=True))
    op.create_index(op.f('ix_products_shared_key'), 'products', ['shared_key'], unique=True)


def downgrade() -> None:
    # Remove shared_key column from products table
    op.drop_index(op.f('ix_products_shared_key'), table_name='products')
    op.drop_column('products', 'shared_key')
