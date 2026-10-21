# backend/alembic/versions/0022_add_profile_retrieved_at.py
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("personal_data_accounts", sa.Column("profile_retrieved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("personal_data_accounts", "profile_retrieved_at")
