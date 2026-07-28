# backend/alembic/versions/0006_add_access_credentials.py
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'access_credentials',
        sa.Column('id',           sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column('site_id',      sa.String(),   sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('cli_username', sa.String(),   nullable=True),
        sa.Column('cli_password', sa.String(),   nullable=True),
        sa.Column('web_username', sa.String(),   nullable=True),
        sa.Column('web_password', sa.String(),   nullable=True),
        sa.Column('db_username',  sa.String(),   nullable=True),
        sa.Column('db_password',  sa.String(),   nullable=True),
        sa.Column('vpn_username', sa.String(),   nullable=True),
        sa.Column('vpn_password', sa.String(),   nullable=True),
        sa.Column('note',         sa.Text(),     nullable=True),
    )


def downgrade() -> None:
    op.drop_table('access_credentials')
