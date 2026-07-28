# backend/alembic/versions/0009_add_credential_ip_port.py
from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('access_credentials', sa.Column('cli_ip',   sa.String(), nullable=True))
    op.add_column('access_credentials', sa.Column('cli_port', sa.String(), nullable=True))
    op.add_column('access_credentials', sa.Column('web_ip',   sa.String(), nullable=True))
    op.add_column('access_credentials', sa.Column('web_port', sa.String(), nullable=True))
    op.add_column('access_credentials', sa.Column('db_ip',    sa.String(), nullable=True))
    op.add_column('access_credentials', sa.Column('db_port',  sa.String(), nullable=True))
    op.add_column('access_credentials', sa.Column('vpn_ip',   sa.String(), nullable=True))
    op.add_column('access_credentials', sa.Column('vpn_port', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('access_credentials', 'vpn_port')
    op.drop_column('access_credentials', 'vpn_ip')
    op.drop_column('access_credentials', 'db_port')
    op.drop_column('access_credentials', 'db_ip')
    op.drop_column('access_credentials', 'web_port')
    op.drop_column('access_credentials', 'web_ip')
    op.drop_column('access_credentials', 'cli_port')
    op.drop_column('access_credentials', 'cli_ip')
