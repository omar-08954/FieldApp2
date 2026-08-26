"""Keep complete import rows and identify the failing column."""
from alembic import op
import sqlalchemy as sa

revision = "20260826_04"
down_revision = "20260816_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("import_reviews", sa.Column("task_status", sa.String(length=80), nullable=True))
    op.add_column("import_reviews", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("import_reviews", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("import_reviews", sa.Column("execution_date", sa.Date(), nullable=True))
    op.add_column("import_reviews", sa.Column("field_name", sa.String(length=80), nullable=True))
    op.add_column("import_reviews", sa.Column("suggested_action", sa.Text(), nullable=True))


def downgrade() -> None:
    for column in ("suggested_action", "field_name", "execution_date", "notes", "city", "task_status"):
        op.drop_column("import_reviews", column)
