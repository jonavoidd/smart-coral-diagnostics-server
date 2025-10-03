"""add bleaching alert table

Revision ID: df5c25358e4e
Revises: ed683d780e9e
Create Date: 2025-09-30 15:38:33.421559

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "df5c25358e4e"
down_revision: Union[str, Sequence[str], None] = "ed683d780e9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bleaching_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("location_key", sa.String(100), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("area_name", sa.String(255), nullable=True),
        sa.Column("bleaching_count", sa.Integer, nullable=False),
        sa.Column("severity_level", sa.String(20), nullable=False),
        sa.Column("alert_message", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column(
            "first_detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )

    op.create_index(
        "idx_bleaching_alerts_location", "bleaching_alerts", ["location_key"]
    )
    op.create_index("idx_bleaching_alerts_active", "bleaching_alerts", ["is_active"])
    op.create_index(
        "idx_bleaching_alerts_severity", "bleaching_alerts", ["severity_level"]
    )
    op.create_index(
        "idx_bleaching_alerts_updated", "bleaching_alerts", ["last_updated_at"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("bleaching_alerts")
