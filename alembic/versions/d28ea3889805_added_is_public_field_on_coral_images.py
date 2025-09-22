"""added is_public field on coral images

Revision ID: d28ea3889805
Revises: 37fb218fa4dd
Create Date: 2025-09-03 14:01:16.822953

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd28ea3889805'
down_revision: Union[str, Sequence[str], None] = '37fb218fa4dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
