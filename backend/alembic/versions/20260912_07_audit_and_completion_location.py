"""Add audit records and optional completion coordinates.

Revision ID: 20260912_07
Revises: 20260826_06
"""
from alembic import op
import sqlalchemy as sa

revision = "20260912_07"
down_revision = "20260826_06"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("assigned_tasks", sa.Column("completion_latitude", sa.Float(), nullable=True))
    op.add_column("assigned_tasks", sa.Column("completion_longitude", sa.Float(), nullable=True))
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_column("assigned_tasks", "completion_longitude")
    op.drop_column("assigned_tasks", "completion_latitude")
