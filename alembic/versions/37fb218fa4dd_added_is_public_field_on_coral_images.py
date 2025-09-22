"""added is_public field on coral images

Revision ID: 37fb218fa4dd
Revises: a63a1a4873a2
Create Date: 2025-09-03 14:01:11.221414

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "37fb218fa4dd"
down_revision: Union[str, Sequence[str], None] = "a63a1a4873a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "coral_images",
        sa.Column(
            "is_public", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )

    op.execute("UPDATE coral_images SET is_public = TRUE")

    op.alter_column("coral_images", "is_public", server_default=None)
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
