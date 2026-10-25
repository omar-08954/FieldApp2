"""Store before and after photos for field tasks."""
from alembic import op
import sqlalchemy as sa

revision = "20261025_14"
down_revision = "20261001_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("photo_type", sa.String(20), nullable=False),
        sa.Column("image_key", sa.String(500), nullable=False),
        sa.Column("image_mime", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_task_photos_task_id", "task_photos", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_task_photos_task_id", table_name="task_photos")
    op.drop_table("task_photos")
