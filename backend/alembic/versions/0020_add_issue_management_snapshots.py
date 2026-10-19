# backend/alembic/versions/0020_add_issue_management_snapshots.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "issue_management_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_key", sa.String(128), nullable=False, unique=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("full_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("issue_management_snapshots")
