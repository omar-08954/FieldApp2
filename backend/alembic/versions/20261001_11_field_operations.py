"""Add field operations metadata, SLA fields, and customer feedback."""
from alembic import op
import sqlalchemy as sa

revision = "20261001_11"
down_revision = "20260930_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = [
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("customer_phone", sa.String(length=40), nullable=True),
        sa.Column("customer_signature", sa.Text(), nullable=True),
        sa.Column("customer_rating", sa.Integer(), nullable=True),
        sa.Column("customer_feedback", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
    ]
    for column in columns:
        op.add_column("tasks", column)
    op.create_index("ix_tasks_due_at", "tasks", ["due_at"])
    op.create_index("ix_tasks_customer_rating", "tasks", ["customer_rating"])


def downgrade() -> None:
    op.drop_index("ix_tasks_customer_rating", table_name="tasks")
    op.drop_index("ix_tasks_due_at", table_name="tasks")
    for name in ("due_at", "longitude", "latitude", "customer_feedback", "customer_rating", "customer_signature", "customer_phone", "customer_name"):
        op.drop_column("tasks", name)
