"""add slug column

Revision ID: 512766f8258b
Revises: aca2a02322c2
Create Date: 2026-03-10 12:44:34.453472
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '512766f8258b'
down_revision: Union[str, Sequence[str], None] = 'aca2a02322c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Add slug column
    op.add_column('companies', sa.Column('slug', sa.String(length=255), nullable=True))

    # Create unique index for slug
    op.create_index('ix_companies_slug', 'companies', ['slug'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""

    # Drop index
    op.drop_index('ix_companies_slug', table_name='companies')

    # Drop column
    op.drop_column('companies', 'slug')