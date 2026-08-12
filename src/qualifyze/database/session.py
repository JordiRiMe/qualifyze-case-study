from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.config import DatabaseConfig


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