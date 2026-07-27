# backend/alembic/versions/0005_create_site_tables.py
import sqlalchemy as sa
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sites',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('site_name', sa.String(), nullable=False),
        sa.Column('maintenance_company', sa.String(), nullable=False),
        sa.Column('customer_name', sa.String(), nullable=False),
        sa.Column('customer_phone', sa.String(), nullable=False),
        sa.Column('customer_email', sa.String(), nullable=True),
        sa.Column('maintenance_name', sa.String(), nullable=False),
        sa.Column('maintenance_phone', sa.String(), nullable=False),
        sa.Column('maintenance_email', sa.String(), nullable=True),
        sa.Column('contract_start_date', sa.Date(), nullable=False),
        sa.Column('contract_end_date', sa.Date(), nullable=False),
        sa.Column('contract_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'deployment_nodes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_id', sa.String(), nullable=False),
        sa.Column('hostname', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('cpu_cores', sa.Integer(), nullable=False),
        sa.Column('cpu_threads', sa.Integer(), nullable=False),
        sa.Column('memory_total_gb', sa.Integer(), nullable=False),
        sa.Column('disk_total_gb', sa.Integer(), nullable=False),
        sa.Column('os_type', sa.String(), nullable=False),
        sa.Column('os_version', sa.String(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('disk_free_gb', sa.Integer(), nullable=True),
        sa.Column('disk_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'solution_packages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('installer_filename', sa.String(), nullable=False),
        sa.Column('license_capacity_gb', sa.Float(), nullable=False),
        sa.Column('deployment_type', sa.String(), nullable=False),
        sa.Column('license_key', sa.String(), nullable=True),
        sa.Column('license_expire_date', sa.Date(), nullable=True),
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id'),
    )

    op.create_table(
        'patch_histories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_id', sa.String(), nullable=False),
        sa.Column('issue_link', sa.Text(), nullable=False),
        sa.Column('patch_date', sa.Date(), nullable=False),
        sa.Column('patch_file_link', sa.Text(), nullable=False),
        sa.Column('patch_type', sa.String(), nullable=False),
        sa.Column('applied_by', sa.String(), nullable=False, server_default=''),
        sa.Column('result_status', sa.String(), nullable=False),
        sa.Column('rollback_date', sa.Date(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'visit_histories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_id', sa.String(), nullable=False),
        sa.Column('visit_date', sa.Date(), nullable=False),
        sa.Column('visitor', sa.String(), nullable=False),
        sa.Column('visit_type', sa.String(), nullable=False),
        sa.Column('visit_summary', sa.Text(), nullable=False),
        sa.Column('next_visit_scheduled', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('visit_histories')
    op.drop_table('patch_histories')
    op.drop_table('solution_packages')
    op.drop_table('deployment_nodes')
    op.drop_table('sites')
