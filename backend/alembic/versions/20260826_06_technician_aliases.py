"""Remember corrected technician names for future Excel imports."""
from alembic import op
import sqlalchemy as sa

revision = "20260826_06"
down_revision = "20260826_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "technician_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alias_name", sa.String(length=200), nullable=False),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_technician_aliases_alias_name", "technician_aliases", ["alias_name"], unique=True)
    op.create_index("ix_technician_aliases_technician_id", "technician_aliases", ["technician_id"])


def downgrade() -> None:
    op.drop_index("ix_technician_aliases_technician_id", table_name="technician_aliases")
    op.drop_index("ix_technician_aliases_alias_name", table_name="technician_aliases")
    op.drop_table("technician_aliases")
