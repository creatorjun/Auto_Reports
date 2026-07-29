# backend/alembic/versions/0010_rebuild_visit_histories.py
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("visit_histories")

    op.create_table(
        "visit_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("visit_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engineer_name", sa.String(), nullable=True),
        sa.Column("engineer_phone", sa.String(), nullable=True),
        sa.Column("request_content", sa.Text(), nullable=True),
        sa.Column("action_content", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("visit_histories")

    op.create_table(
        "visit_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.String(), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("visitor", sa.String(), nullable=False),
        sa.Column("visit_type", sa.String(), nullable=False),
        sa.Column("visit_summary", sa.Text(), nullable=False),
        sa.Column("next_visit_scheduled", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
