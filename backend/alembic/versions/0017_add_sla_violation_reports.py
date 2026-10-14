# backend/alembic/versions/0017_add_sla_violation_reports.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sla_violation_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("selected_date", sa.Date(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", sa.String(255), nullable=False),
        sa.Column("ticket_count", sa.Integer(), nullable=False),
        sa.Column("initial_response_count", sa.Integer(), nullable=False),
        sa.Column("resolution_count", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_sla_violation_reports_generated_at_id", "sla_violation_reports", ["generated_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_sla_violation_reports_generated_at_id", table_name="sla_violation_reports")
    op.drop_table("sla_violation_reports")
