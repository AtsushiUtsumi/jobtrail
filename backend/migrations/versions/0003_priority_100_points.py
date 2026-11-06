"""priority 100 points

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 5 段階から 100 点満点へ。段階の位置が保たれるよう 20 倍する。
    op.execute("UPDATE companies SET priority = priority * 20 WHERE priority IS NOT NULL")


def downgrade() -> None:
    # 5 段階に丸める。0 点は最低の 1 に寄せる。
    op.execute(
        "UPDATE companies SET priority = GREATEST(ROUND(priority / 20.0), 1) "
        "WHERE priority IS NOT NULL"
    )
