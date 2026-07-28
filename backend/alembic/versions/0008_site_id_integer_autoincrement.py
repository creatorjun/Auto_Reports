# backend/alembic/versions/0008_site_id_integer_autoincrement.py
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('access_credentials') as batch_op:
        batch_op.drop_constraint('access_credentials_site_id_fkey', type_='foreignkey')
    with op.batch_alter_table('deployment_nodes') as batch_op:
        batch_op.drop_constraint('deployment_nodes_site_id_fkey', type_='foreignkey')
    with op.batch_alter_table('patch_histories') as batch_op:
        batch_op.drop_constraint('patch_histories_site_id_fkey', type_='foreignkey')
    with op.batch_alter_table('solution_packages') as batch_op:
        batch_op.drop_constraint('solution_packages_site_id_fkey', type_='foreignkey')
    with op.batch_alter_table('visit_histories') as batch_op:
        batch_op.drop_constraint('visit_histories_site_id_fkey', type_='foreignkey')

    with op.batch_alter_table('sites') as batch_op:
        batch_op.alter_column('id',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using='id::integer')

    with op.batch_alter_table('access_credentials') as batch_op:
        batch_op.alter_column('site_id',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using='site_id::integer')
        batch_op.create_foreign_key('access_credentials_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('deployment_nodes') as batch_op:
        batch_op.alter_column('site_id',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using='site_id::integer')
        batch_op.create_foreign_key('deployment_nodes_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('patch_histories') as batch_op:
        batch_op.alter_column('site_id',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using='site_id::integer')
        batch_op.create_foreign_key('patch_histories_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('solution_packages') as batch_op:
        batch_op.alter_column('site_id',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using='site_id::integer')
        batch_op.create_foreign_key('solution_packages_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('visit_histories') as batch_op:
        batch_op.alter_column('site_id',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using='site_id::integer')
        batch_op.create_foreign_key('visit_histories_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    op.execute("CREATE SEQUENCE IF NOT EXISTS sites_id_seq")
    op.execute("SELECT setval('sites_id_seq', COALESCE((SELECT MAX(id) FROM sites), 0) + 1, false)")
    op.execute("ALTER TABLE sites ALTER COLUMN id SET DEFAULT nextval('sites_id_seq')")


def downgrade() -> None:
    with op.batch_alter_table('access_credentials') as batch_op:
        batch_op.drop_constraint('access_credentials_site_id_fkey', type_='foreignkey')
    with op.batch_alter_table('deployment_nodes') as batch_op:
        batch_op.drop_constraint('deployment_nodes_site_id_fkey', type_='foreignkey')
    with op.batch_alter_table('patch_histories') as batch_op:
        batch_op.drop_constraint('patch_histories_site_id_fkey', type_='foreignkey')
    with op.batch_alter_table('solution_packages') as batch_op:
        batch_op.drop_constraint('solution_packages_site_id_fkey', type_='foreignkey')
    with op.batch_alter_table('visit_histories') as batch_op:
        batch_op.drop_constraint('visit_histories_site_id_fkey', type_='foreignkey')

    with op.batch_alter_table('sites') as batch_op:
        batch_op.alter_column('id',
            existing_type=sa.Integer(),
            type_=sa.String(),
            existing_nullable=False)

    with op.batch_alter_table('access_credentials') as batch_op:
        batch_op.alter_column('site_id', existing_type=sa.Integer(), type_=sa.String(), existing_nullable=False)
        batch_op.create_foreign_key('access_credentials_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('deployment_nodes') as batch_op:
        batch_op.alter_column('site_id', existing_type=sa.Integer(), type_=sa.String(), existing_nullable=False)
        batch_op.create_foreign_key('deployment_nodes_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('patch_histories') as batch_op:
        batch_op.alter_column('site_id', existing_type=sa.Integer(), type_=sa.String(), existing_nullable=False)
        batch_op.create_foreign_key('patch_histories_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('solution_packages') as batch_op:
        batch_op.alter_column('site_id', existing_type=sa.Integer(), type_=sa.String(), existing_nullable=False)
        batch_op.create_foreign_key('solution_packages_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('visit_histories') as batch_op:
        batch_op.alter_column('site_id', existing_type=sa.Integer(), type_=sa.String(), existing_nullable=False)
        batch_op.create_foreign_key('visit_histories_site_id_fkey', 'sites', ['site_id'], ['id'], ondelete='CASCADE')
