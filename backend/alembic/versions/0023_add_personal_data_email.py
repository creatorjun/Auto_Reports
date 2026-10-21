# backend/alembic/versions/0023_add_personal_data_email.py
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("personal_data_accounts", sa.Column("email_address", sa.String(320), nullable=True))


def downgrade() -> None:
    op.drop_column("personal_data_accounts", "email_address")
