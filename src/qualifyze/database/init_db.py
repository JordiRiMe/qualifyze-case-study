from qualifyze.config import Settings
from qualifyze.database import Base
from qualifyze.database.session import create_database_engine


def main() -> None:
    config = Settings()  # type: ignore
    engine = create_database_engine(config.database)

    Base.metadata.create_all(engine)


if __name__ == "__main__":
    main()
