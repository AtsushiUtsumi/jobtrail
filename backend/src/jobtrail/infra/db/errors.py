from sqlalchemy.exc import IntegrityError

from jobtrail.domain.shared.errors import ConflictError, DomainError, DuplicateCompanyError


def translate_integrity_error(error: IntegrityError) -> DomainError:
    if "ux_companies_" in str(error.orig):
        return DuplicateCompanyError(None, "同時に登録された企業")
    return ConflictError()
