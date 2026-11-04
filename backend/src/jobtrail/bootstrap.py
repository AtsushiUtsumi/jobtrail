"""合成ルート。infra の実装をユースケースへ渡す。"""

from jobtrail.config import get_settings
from jobtrail.infra.db.models import start_mappers
from jobtrail.infra.db.session import create_session_factory
from jobtrail.infra.unit_of_work import SqlAlchemyUnitOfWork
from jobtrail.usecase.context import AppContext


def build_context() -> AppContext:
    settings = get_settings()
    start_mappers()
    session_factory = create_session_factory(settings.database_url)
    return AppContext(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        settings=settings,
    )
