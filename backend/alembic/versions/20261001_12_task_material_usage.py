"""Link inventory consumption to field tasks."""
from alembic import op
import sqlalchemy as sa

revision = "20261001_12"
down_revision = "20261001_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_material_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_task_material_usage_task_id", "task_material_usage", ["task_id"])
    op.create_index("ix_task_material_usage_material_id", "task_material_usage", ["material_id"])
    op.create_index("ix_task_material_usage_actor_id", "task_material_usage", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_task_material_usage_actor_id", table_name="task_material_usage")
    op.drop_index("ix_task_material_usage_material_id", table_name="task_material_usage")
    op.drop_index("ix_task_material_usage_task_id", table_name="task_material_usage")
    op.drop_table("task_material_usage")
