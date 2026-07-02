# backend/alembic/versions/0001_create_reports.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('week_end', sa.Date(), nullable=False),
        sa.Column('report_date', sa.String(), nullable=False),
        sa.Column('widgets', JSONB(), nullable=False),
        sa.Column('ai_analysis', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reports_week_start', 'reports', ['week_start'])


def downgrade() -> None:
    op.drop_index('ix_reports_week_start', table_name='reports')
    op.drop_table('reports')
