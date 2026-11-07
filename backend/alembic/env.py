import asyncio
from logging.config import fileConfig
from sqlalchemy import pool, engine_from_config, engine_from_config
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from alembic.operations.batch import BatchOperationsImpl
from app.core.config import settings
from app.db.base import Base
import app.models.entities
from sqlalchemy import ForeignKeyConstraint

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
if settings.database_url:
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

target_metadata = Base.metadata
constraint_naming_convention = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}

_batch_add_constraint = BatchOperationsImpl.add_constraint


def _batch_add_constraint_with_fk_name(self, constraint):
    if isinstance(constraint, ForeignKeyConstraint) and constraint.name is None:
        column_name = next(iter(constraint.columns)).name
        referred_table = constraint.elements[0].column.table.name
        constraint.name = (
            f"fk_{self.table_name}_{column_name}_{referred_table}"
        )
    return _batch_add_constraint(self, constraint)


# Released revision 0006 adds an unnamed FK in SQLite batch mode; naming it here
# keeps that immutable migration executable for existing SQLite installations.
BatchOperationsImpl.add_constraint = _batch_add_constraint_with_fk_name


def run_migrations_offline() -> None:
    url = settings.database_url or config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        naming_convention=constraint_naming_convention,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online_sync() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    migration_url = settings.database_url or config.get_main_option("sqlalchemy.url")
    if migration_url.startswith("sqlite:///") or migration_url.startswith("postgresql://"):
        run_migrations_online_sync()
    else:
        asyncio.run(run_migrations_online())
