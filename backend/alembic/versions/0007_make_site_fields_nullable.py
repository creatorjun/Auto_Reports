# backend/alembic/versions/0007_make_site_fields_nullable.py
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

NULLABLE_SITE_COLS = [
    ("maintenance_company", sa.String()),
    ("customer_name",       sa.String()),
    ("customer_phone",      sa.String()),
    ("maintenance_name",    sa.String()),
    ("maintenance_phone",   sa.String()),
    ("contract_start_date", sa.Date()),
    ("contract_end_date",   sa.Date()),
    ("contract_type",       sa.String()),
    ("status",              sa.String()),
]

NULLABLE_NODE_COLS = [
    ("hostname",        sa.String()),
    ("role",            sa.String()),
    ("cpu_cores",       sa.Integer()),
    ("cpu_threads",     sa.Integer()),
    ("memory_total_gb", sa.Integer()),
    ("disk_total_gb",   sa.Integer()),
    ("os_type",         sa.String()),
    ("os_version",      sa.String()),
]

NULLABLE_PKG_COLS = [
    ("version",             sa.String()),
    ("installer_filename",  sa.String()),
    ("license_capacity_gb", sa.Float()),
    ("deployment_type",     sa.String()),
]

NULLABLE_PATCH_COLS = [
    ("issue_link",      sa.Text()),
    ("patch_date",      sa.Date()),
    ("patch_file_link", sa.Text()),
    ("patch_type",      sa.String()),
    ("applied_by",      sa.String()),
    ("result_status",   sa.String()),
]

NULLABLE_VISIT_COLS = [
    ("visit_date",    sa.Date()),
    ("visitor",       sa.String()),
    ("visit_type",    sa.String()),
    ("visit_summary", sa.Text()),
]


def _alter_nullable(table: str, cols: list, existing_nullable: bool) -> None:
    for col, col_type in cols:
        op.alter_column(
            table, col,
            existing_type=col_type,
            nullable=True,
            existing_nullable=existing_nullable,
        )


def _alter_not_null(table: str, cols: list) -> None:
    for col, col_type in cols:
        op.alter_column(
            table, col,
            existing_type=col_type,
            nullable=False,
            existing_nullable=True,
        )


def upgrade() -> None:
    _alter_nullable("sites",             NULLABLE_SITE_COLS,  existing_nullable=False)
    _alter_nullable("deployment_nodes",  NULLABLE_NODE_COLS,  existing_nullable=False)
    _alter_nullable("solution_packages", NULLABLE_PKG_COLS,   existing_nullable=False)
    _alter_nullable("patch_histories",   NULLABLE_PATCH_COLS, existing_nullable=False)
    _alter_nullable("visit_histories",   NULLABLE_VISIT_COLS, existing_nullable=False)


def downgrade() -> None:
    _alter_not_null("visit_histories",   NULLABLE_VISIT_COLS)
    _alter_not_null("patch_histories",   NULLABLE_PATCH_COLS)
    _alter_not_null("solution_packages", NULLABLE_PKG_COLS)
    _alter_not_null("deployment_nodes",  NULLABLE_NODE_COLS)
    _alter_not_null("sites",             NULLABLE_SITE_COLS)
