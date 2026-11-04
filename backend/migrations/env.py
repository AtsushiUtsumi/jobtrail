from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from jobtrail.config import get_settings
from jobtrail.infra.db.models import metadata

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)


def run_migrations() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
