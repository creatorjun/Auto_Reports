# 삭제: 0002 마이그레이션 롱래퍼 파일 (0001로 롤백)
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass  # no-op: created_at stays as DateTime (no timezone)


def downgrade() -> None:
    pass
