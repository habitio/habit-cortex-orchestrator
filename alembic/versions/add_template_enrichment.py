"""
Add data_requirements and attachments_config to email templates.

Revision ID: add_template_enrichment
Revises: previous_migration
Create Date: 2026-01-24 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_template_enrichment'
down_revision = None  # Replace with actual previous revision ID
branch_labels = None
depends_on = None


def upgrade():
    """Add data enrichment and attachment configuration to email templates."""
    
    # Add data_requirements column (JSONB)
    op.add_column(
        'email_templates',
        sa.Column(
            'data_requirements',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default='{}'
        )
    )
    
    # Add attachments_config column (JSONB)
    op.add_column(
        'email_templates',
        sa.Column(
            'attachments_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default='[]'
        )
    )


def downgrade():
    """Remove data enrichment and attachment configuration columns."""
    
    op.drop_column('email_templates', 'data_requirements')
    op.drop_column('email_templates', 'attachments_config')
