from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.orm import Session

from jobtrail.domain.application.application import Application
from jobtrail.domain.application.job_posting import JobPostingSnapshot
from jobtrail.domain.application.repository import ApplicationRow, StageRow
from jobtrail.domain.shared.ids import ApplicationId, JobPostingId
from jobtrail.infra.db.models import applications, companies, job_postings, stages


class SqlApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, application: Application) -> None:
        self._session.add(application)

    def get(self, application_id: ApplicationId) -> Application | None:
        return self._session.get(Application, application_id)


class SqlApplicationReadRepository:
    """集約を経由せず Core で直接読む。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def rows(self) -> Sequence[ApplicationRow]:
        stages_by_application: dict[ApplicationId, list[StageRow]] = defaultdict(list)
        for row in self._session.execute(
            sa.select(stages).order_by(stages.c.application_id, stages.c.position)
        ).mappings():
            stages_by_application[row["application_id"]].append(
                StageRow(
                    id=row["id"],
                    type=row["type"],
                    label=row["label"],
                    result=row["result"],
                    scheduled_at=row["scheduled_at"],
                    created_at=row["created_at"],
                    result_recorded_at=row["result_recorded_at"],
                )
            )
        query = (
            sa.select(applications, companies.c.name.label("company_name"))
            .join(companies, companies.c.id == applications.c.company_id)
            .where(companies.c.deleted_at.is_(None))
        )
        return [
            ApplicationRow(
                id=row["id"],
                company_id=row["company_id"],
                company_name=row["company_name"],
                position=row["position"],
                channel=row["channel"],
                applied_at=row["applied_at"],
                outcome=row["outcome"],
                submitted_document_version_id=row["submitted_document_version_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                version=row["version"],
                stages=tuple(stages_by_application[row["id"]]),
            )
            for row in self._session.execute(query).mappings()
        ]


class SqlJobPostingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, posting: JobPostingSnapshot) -> None:
        self._session.add(posting)

    def get(self, posting_id: JobPostingId) -> JobPostingSnapshot | None:
        return self._session.get(JobPostingSnapshot, posting_id)

    def latest(self, application_id: ApplicationId) -> JobPostingSnapshot | None:
        return self._session.scalars(
            sa.select(JobPostingSnapshot)
            .where(job_postings.c.application_id == application_id)
            .order_by(job_postings.c.revision.desc())
            .limit(1)
        ).first()

    def list_for_application(self, application_id: ApplicationId) -> Sequence[JobPostingSnapshot]:
        return self._session.scalars(
            sa.select(JobPostingSnapshot)
            .where(job_postings.c.application_id == application_id)
            .order_by(job_postings.c.revision.desc())
        ).all()
