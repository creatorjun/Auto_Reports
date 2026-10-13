# backend/alembic/versions/0015_add_c_level_reports.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "c_level_comments",
        sa.Column("issue_key", sa.String(100), primary_key=True),
        sa.Column("delay_reason", sa.Text(), nullable=False),
        sa.Column("action_taken", sa.Text(), nullable=False),
        sa.Column("prevention_plan", sa.Text(), nullable=False),
        sa.Column("included", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "c_level_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("saved_by", sa.String(255), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_c_level_snapshots_saved_at", "c_level_snapshots", ["saved_at"])


def downgrade() -> None:
    op.drop_index("ix_c_level_snapshots_saved_at", table_name="c_level_snapshots")
    op.drop_table("c_level_snapshots")
    op.drop_table("c_level_comments")
