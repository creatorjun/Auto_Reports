# backend/alembic/versions/0024_add_jira_login_users.py
from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jira_login_users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("cloud_id", sa.String(100), nullable=False),
        sa.Column("account_id", sa.String(128), sa.ForeignKey("personal_data_accounts.account_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cloud_id", "account_id", name="uq_jira_login_user_identity"),
    )
    op.create_index("ix_jira_login_users_account_id", "jira_login_users", ["account_id"])
    op.create_table(
        "jira_login_authorizations",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("jira_login_users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "jira_login_devices",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("jira_login_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=True, unique=True),
        sa.Column("session_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_jira_login_devices_user_id", "jira_login_devices", ["user_id"])
    op.create_index("ix_jira_login_devices_expires_at", "jira_login_devices", ["expires_at"])


def downgrade() -> None:
    op.drop_table("jira_login_devices")
    op.drop_table("jira_login_authorizations")
    op.drop_table("jira_login_users")
