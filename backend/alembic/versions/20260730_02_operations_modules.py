"""Add assignments, materials, daily reports, and indexes.

Revision ID: 20260730_02
Revises: 20260730_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20260730_02"
down_revision = "20260730_01"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("assigned_tasks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("task_number", sa.String(120), nullable=False), sa.Column("subscription_number", sa.String(120), nullable=False), sa.Column("task_type", sa.String(80), nullable=False), sa.Column("task_status", sa.String(80), nullable=False), sa.Column("city", sa.String(120)), sa.Column("notes", sa.Text()), sa.Column("assigned_date", sa.Date(), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("assigned_by_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("materials", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(160), nullable=False, unique=True), sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"), sa.Column("unit", sa.String(40), nullable=False), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("daily_reports", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("report_date", sa.Date(), nullable=False), sa.Column("image_key", sa.String(500), nullable=False), sa.Column("image_mime", sa.String(80), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("technician_id", "report_date", name="uq_daily_report_technician_date"))
    op.create_index("ix_assigned_tasks_technician_id", "assigned_tasks", ["technician_id"])
    op.create_index("ix_materials_name", "materials", ["name"])

def downgrade() -> None:
    op.drop_table("daily_reports"); op.drop_table("materials"); op.drop_table("assigned_tasks")
