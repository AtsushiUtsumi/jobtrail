"""priority on application

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("priority", sa.Integer(), nullable=True))
    # 企業の点数は、その企業の全応募へ引き継ぐ。
    op.execute(
        "UPDATE applications AS a SET priority = c.priority "
        "FROM companies AS c WHERE c.id = a.company_id"
    )
    op.drop_column("companies", "priority")


def downgrade() -> None:
    op.add_column("companies", sa.Column("priority", sa.Integer(), nullable=True))
    # 企業には 1 つの点数しか持てないので、応募の最高点を採る。
    op.execute(
        """
        UPDATE companies AS c
        SET priority = best.priority
        FROM (
            SELECT company_id, MAX(priority) AS priority
            FROM applications
            GROUP BY company_id
        ) AS best
        WHERE best.company_id = c.id
        """
    )
    op.drop_column("applications", "priority")
