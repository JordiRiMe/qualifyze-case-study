from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.config import DatabaseConfig
from qualifyze.database import Base


def create_database_engine(config: DatabaseConfig) -> Engine:
    return create_engine(
        config.sqlalchemy_url,
        pool_pre_ping=True,
    )

def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

def create_database_tables(
    engine: Engine,
) -> None:
    # Importing the models registers their tables in
    # Base.metadata before create_all() is executed.
    import qualifyze.database.models  # noqa: F401

    Base.metadata.create_all(
        bind=engine,
    )
