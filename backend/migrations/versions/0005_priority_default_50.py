"""priority default 50

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 未評価という状態をなくす。既定値はアプリ側で与える。
    op.execute("UPDATE applications SET priority = 50 WHERE priority IS NULL")
    op.alter_column("applications", "priority", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column("applications", "priority", existing_type=sa.Integer(), nullable=True)
