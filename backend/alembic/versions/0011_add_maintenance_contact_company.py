# backend/alembic/versions/0011_add_maintenance_contact_company.py
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sites",
        sa.Column("maintenance_contact_company", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sites", "maintenance_contact_company")
