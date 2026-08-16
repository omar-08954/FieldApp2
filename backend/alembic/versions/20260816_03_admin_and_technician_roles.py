"""Restrict FieldApp accounts to administrators and technicians.

Revision ID: 20260816_03
Revises: 20260730_02
Create Date: 2026-08-16
"""
from alembic import op

revision = "20260816_03"
down_revision = "20260730_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing managers retain their operational access as administrators.
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'manager'")


def downgrade() -> None:
    # The original manager/admin distinction cannot be recovered reliably.
    pass
