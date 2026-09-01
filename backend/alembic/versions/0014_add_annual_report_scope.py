# backend/alembic/versions/0014_add_annual_report_scope.py
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("scope", sa.String(), nullable=False, server_default="standard"),
    )
    op.add_column(
        "reports",
        sa.Column("report_year", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE reports
        SET
            scope = 'annual',
            report_year = EXTRACT(YEAR FROM week_start)::integer
        WHERE EXTRACT(MONTH FROM week_start) = 1
          AND EXTRACT(DAY FROM week_start) = 1
          AND EXTRACT(YEAR FROM week_start) = EXTRACT(YEAR FROM week_end)
          AND (
              (EXTRACT(MONTH FROM week_end) = 12 AND EXTRACT(DAY FROM week_end) = 31)
              OR EXTRACT(YEAR FROM week_start) = EXTRACT(YEAR FROM CURRENT_DATE)
          )
        """
    )
    op.create_index(
        "ix_reports_scope_year_created_at",
        "reports",
        ["scope", "report_year", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_reports_scope_year_created_at", table_name="reports")
    op.drop_column("reports", "report_year")
    op.drop_column("reports", "scope")
