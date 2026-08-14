import logging

from qualifyze.config import Settings
from qualifyze.database.repositories.warning_letters import (
    WarningLetterRepository,
)
from qualifyze.database.session import (
    create_database_engine,
    create_session_factory,
)
from qualifyze.services.ingestion.warning_letters import (
    WarningLetterIngestionService,
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(name)s | "
        "%(levelname)s | %(message)s"
    ),
)


def main() -> None:
    config = Settings()  # type: ignore

    engine = create_database_engine(config.database)
    session_factory = create_session_factory(engine)
    repository = WarningLetterRepository(session_factory)

    service = WarningLetterIngestionService(
        retriever_config=config.warning_letters,
        repository=repository,
        batch_size=10,
        known_batches_before_stop=None,
    )

    try:
        result = service.run_once()

        logger.info(
            "Test result: %s",
            result,
        )
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()