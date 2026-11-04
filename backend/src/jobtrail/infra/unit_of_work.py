from types import TracebackType
from typing import Self

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from jobtrail.domain.application.repository import (
    ApplicationReadRepository,
    ApplicationRepository,
    JobPostingRepository,
)
from jobtrail.domain.company.repository import CompanyRepository, CompanySourceRepository
from jobtrail.domain.document.repository import DocumentRepository
from jobtrail.domain.shared.errors import ConflictError
from jobtrail.domain.skill_profile.repository import (
    SkillProfileRepository,
    SubmissionRepository,
)
from jobtrail.infra.db.errors import translate_integrity_error
from jobtrail.infra.db.repositories.application import (
    SqlApplicationReadRepository,
    SqlApplicationRepository,
    SqlJobPostingRepository,
)
from jobtrail.infra.db.repositories.company import (
    SqlCompanyRepository,
    SqlCompanySourceRepository,
)
from jobtrail.infra.db.repositories.document import SqlDocumentRepository
from jobtrail.infra.db.repositories.skill_profile import (
    SqlSkillProfileRepository,
    SqlSubmissionRepository,
)


class SqlAlchemyUnitOfWork:
    companies: CompanyRepository
    company_sources: CompanySourceRepository
    applications: ApplicationRepository
    application_reads: ApplicationReadRepository
    job_postings: JobPostingRepository
    documents: DocumentRepository
    skill_profile: SkillProfileRepository
    submissions: SubmissionRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        session = self._session_factory()
        self._session = session
        self.companies = SqlCompanyRepository(session)
        self.company_sources = SqlCompanySourceRepository(session)
        self.applications = SqlApplicationRepository(session)
        self.application_reads = SqlApplicationReadRepository(session)
        self.job_postings = SqlJobPostingRepository(session)
        self.documents = SqlDocumentRepository(session)
        self.skill_profile = SqlSkillProfileRepository(session)
        self.submissions = SqlSubmissionRepository(session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._session.rollback()
        self._session.close()

    def commit(self) -> None:
        try:
            self._session.commit()
        except StaleDataError as error:
            raise ConflictError() from error
        except IntegrityError as error:
            raise translate_integrity_error(error) from error

    def check_connection(self) -> None:
        self._session.execute(sa.text("SELECT 1"))
