"""Initial enterprise FieldApp schema.

Revision ID: 20260730_01
Revises:
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "20260730_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(80), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("full_name", sa.String(200), nullable=False), sa.Column("role", sa.String(30), nullable=False), sa.Column("city", sa.String(120)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("tasks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("technician_name", sa.String(200), nullable=False, server_default="غير مسجل"), sa.Column("task_number", sa.String(120), nullable=False), sa.Column("subscription_number", sa.String(120), nullable=False, server_default="غير مسجل"), sa.Column("task_type", sa.String(80), nullable=False, server_default="تقني"), sa.Column("task_status", sa.String(80), nullable=False, server_default="تم الفحص"), sa.Column("city", sa.String(120)), sa.Column("notes", sa.Text()), sa.Column("execution_date", sa.Date(), nullable=False), sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_tasks_task_number", "tasks", ["task_number"])
    op.create_index("ix_tasks_subscription_number", "tasks", ["subscription_number"])
    op.create_index("ix_tasks_execution_date", "tasks", ["execution_date"])
    op.create_table("import_batches", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("filename", sa.String(255), nullable=False), sa.Column("imported_by_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"), sa.Column("imported_rows", sa.Integer(), nullable=False, server_default="0"), sa.Column("review_rows", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("import_reviews", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("batch_id", sa.Integer(), sa.ForeignKey("import_batches.id")), sa.Column("source_row", sa.Integer(), nullable=False), sa.Column("task_number", sa.String(120)), sa.Column("technician_name", sa.String(200)), sa.Column("subscription_number", sa.String(120)), sa.Column("task_type", sa.String(80)), sa.Column("exception_type", sa.String(100), nullable=False), sa.Column("error_message", sa.Text(), nullable=False), sa.Column("postgres_message", sa.Text()), sa.Column("action_taken", sa.String(120), nullable=False), sa.Column("raw_payload", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="pending"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("notifications", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("event_type", sa.String(80), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

def downgrade() -> None:
    op.drop_table("notifications"); op.drop_table("import_reviews"); op.drop_table("import_batches"); op.drop_table("tasks"); op.drop_table("users")
