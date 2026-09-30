"""Store last known technician locations for live operations."""
from alembic import op
import sqlalchemy as sa

revision = "20261001_13"
down_revision = "20261001_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "technician_locations",
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_technician_locations_recorded_at", "technician_locations", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_technician_locations_recorded_at", table_name="technician_locations")
    op.drop_table("technician_locations")
