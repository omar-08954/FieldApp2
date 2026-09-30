"""Indexes for operational filters, notification feeds, and cursor ordering."""
from alembic import op

revision = "20260930_09"
down_revision = "20260922_08"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_index("ix_tasks_status_execution_date", "tasks", ["task_status", "execution_date"])
    op.create_index("ix_tasks_technician_execution_date", "tasks", ["technician_id", "execution_date"])
    op.create_index("ix_tasks_city_execution_date", "tasks", ["city", "execution_date"])
    op.create_index("ix_tasks_created_id", "tasks", ["created_at", "id"])
    op.create_index("ix_assigned_tasks_technician_completed_date", "assigned_tasks", ["technician_id", "completed_at", "assigned_date"])
    op.create_index("ix_notifications_user_read_created", "notifications", ["user_id", "is_read", "created_at"])

def downgrade() -> None:
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_index("ix_assigned_tasks_technician_completed_date", table_name="assigned_tasks")
    op.drop_index("ix_tasks_created_id", table_name="tasks")
    op.drop_index("ix_tasks_city_execution_date", table_name="tasks")
    op.drop_index("ix_tasks_technician_execution_date", table_name="tasks")
    op.drop_index("ix_tasks_status_execution_date", table_name="tasks")
