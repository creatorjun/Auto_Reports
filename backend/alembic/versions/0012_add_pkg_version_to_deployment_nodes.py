# backend/alembic/versions/0012_add_pkg_version_to_deployment_nodes.py
from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('deployment_nodes', sa.Column('pkg_version', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('deployment_nodes', 'pkg_version')
