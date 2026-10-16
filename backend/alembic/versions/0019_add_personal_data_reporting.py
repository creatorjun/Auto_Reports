# backend/alembic/versions/0019_add_personal_data_reporting.py
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personal_data_accounts",
        sa.Column("account_id", sa.String(128), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("oldest_retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_report_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_index("ix_personal_data_accounts_next_report_at", "personal_data_accounts", ["next_report_at"])
    op.create_table(
        "personal_data_reporting_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.String(128), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("personal_data_reporting_grants")
    op.drop_index("ix_personal_data_accounts_next_report_at", table_name="personal_data_accounts")
    op.drop_table("personal_data_accounts")
