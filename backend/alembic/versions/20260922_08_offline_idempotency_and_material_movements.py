"""Add offline idempotency and inventory movement history.

Revision ID: 20260922_08
Revises: 20260912_07
"""
from alembic import op
import sqlalchemy as sa

revision = "20260922_08"
down_revision = "20260912_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("idempotency_key", sa.String(length=120), nullable=True))
    op.create_index("ix_tasks_idempotency_key", "tasks", ["idempotency_key"], unique=True)
    op.create_index("ux_tasks_task_number", "tasks", ["task_number"], unique=True)
    op.create_table(
        "material_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("quantity_before", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_material_movements_material_id", "material_movements", ["material_id"])
    op.create_index("ix_material_movements_actor_id", "material_movements", ["actor_id"])
    op.create_index("ix_material_movements_created_at", "material_movements", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_material_movements_created_at", table_name="material_movements")
    op.drop_index("ix_material_movements_actor_id", table_name="material_movements")
    op.drop_index("ix_material_movements_material_id", table_name="material_movements")
    op.drop_table("material_movements")
    op.drop_index("ux_tasks_task_number", table_name="tasks")
    op.drop_index("ix_tasks_idempotency_key", table_name="tasks")
    op.drop_column("tasks", "idempotency_key")
