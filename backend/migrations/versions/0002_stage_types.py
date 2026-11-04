"""stage types

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 廃止する種別の名前は label に残す。downgrade でも使う。
    op.execute(
        "UPDATE stages SET type = 'second_interview', label = COALESCE(label, '最終') "
        "WHERE type = 'final'"
    )
    op.execute(
        "UPDATE stages SET type = 'document', label = COALESCE(label, '適性検査') "
        "WHERE type = 'aptitude'"
    )
    op.execute(
        """
        UPDATE stages AS s
        SET type = CASE WHEN ranked.n = 1 THEN 'first_interview' ELSE 'second_interview' END
        FROM (
            SELECT id, row_number() OVER (PARTITION BY application_id ORDER BY position) AS n
            FROM stages
            WHERE type = 'interview'
        ) AS ranked
        WHERE s.id = ranked.id
        """
    )


def downgrade() -> None:
    op.execute(
        "UPDATE stages SET type = 'final' WHERE type = 'second_interview' AND label LIKE '最終%'"
    )
    op.execute("UPDATE stages SET type = 'aptitude' WHERE type = 'document' AND label = '適性検査'")
    op.execute(
        "UPDATE stages SET type = 'interview' WHERE type IN ('first_interview', 'second_interview')"
    )
