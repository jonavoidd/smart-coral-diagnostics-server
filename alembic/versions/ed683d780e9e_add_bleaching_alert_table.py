"""add_bleaching_alert_table

Revision ID: ed683d780e9e
Revises: ebb033ca0ab4
Create Date: 2025-09-30 15:31:53.466945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed683d780e9e'
down_revision: Union[str, Sequence[str], None] = 'ebb033ca0ab4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
