"""Track intentionally skipped blank and duplicate import rows."""
from alembic import op
import sqlalchemy as sa

revision = "20260826_05"
down_revision = "20260826_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("import_batches", sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("import_batches", "skipped_rows")
