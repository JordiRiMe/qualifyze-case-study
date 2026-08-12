import logging

import httpx

from qualifyze.collector.warnings import (
    WarningLetterParsingError,
    WarningLettersRetriever,
)
from qualifyze.config import WarningLettersRetrieverConfig
from qualifyze.database.repositories.warning_letters import WarningLetterRepository
from qualifyze.typing import IngestionResult

logger = logging.getLogger(__name__)


class WarningLetterIngestionService:
    def __init__(
        self,
        *,
        retriever_config: WarningLettersRetrieverConfig,
        repository: WarningLetterRepository,
        batch_size: int = 10,
        known_batches_before_stop: int | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        self._retriever_config = retriever_config
        self._repository = repository
        self._batch_size = batch_size
        self._known_batches_before_stop = (
            known_batches_before_stop
        )

    def run_once(
        self,
        *,
        max_batches: int | None = None,
    ) -> IngestionResult:
        start = 0
        batches = 0
        discovered = 0
        stored = 0
        failed = 0
        consecutive_known_batches = 0
        seen_urls: set[str] = set()

        logger.info("Starting warning-letter ingestion")

        with WarningLettersRetriever(
            self._retriever_config
        ) as retriever:
            while True:
                letters = retriever.retrieve(
                    start=start,
                    length=self._batch_size,
                )

                batches += 1

                if not letters:
                    logger.info(
                        "No warning letters returned at start=%d",
                        start,
                    )
                    break

                # Protect against unexpected duplicates between batches.
                new_batch_letters = [
                    letter
                    for letter in letters
                    if letter.url not in seen_urls
                ]

                duplicate_count = (
                    len(letters) - len(new_batch_letters)
                )

                if duplicate_count:
                    logger.warning(
                        "Found %d duplicate URLs at start=%d",
                        duplicate_count,
                        start,
                    )

                seen_urls.update(
                    letter.url for letter in letters
                )

                existing_urls = (
                    self._repository.find_existing_urls(
                        letter.url
                        for letter in new_batch_letters
                    )
                )

                missing_letters = [
                    letter
                    for letter in new_batch_letters
                    if letter.url not in existing_urls
                ]

                discovered += len(missing_letters)

                logger.info(
                    (
                        "Batch start=%d returned=%d "
                        "missing=%d existing=%d"
                    ),
                    start,
                    len(letters),
                    len(missing_letters),
                    len(existing_urls),
                )

                if missing_letters:
                    consecutive_known_batches = 0
                else:
                    consecutive_known_batches += 1

                for letter in missing_letters:
                    try:
                        detailed_letter = (
                            retriever.retrieve_detail(letter)
                        )

                        # Each upsert opens and completes its own
                        # short database transaction.
                        self._repository.upsert(
                            detailed_letter
                        )

                        stored += 1

                        logger.info(
                            "Stored warning letter: %s",
                            detailed_letter.url,
                        )

                    except (
                        httpx.HTTPError,
                        WarningLetterParsingError,
                    ):
                        failed += 1

                        logger.exception(
                            "Could not ingest warning letter: %s",
                            letter.url,
                        )

                if len(letters) < self._batch_size:
                    logger.info(
                        "Reached final partial batch"
                    )
                    break

                if (
                    self._known_batches_before_stop is not None
                    and consecutive_known_batches
                    >= self._known_batches_before_stop
                ):
                    logger.info(
                        (
                            "Stopping after %d consecutive "
                            "fully known batches"
                        ),
                        consecutive_known_batches,
                    )
                    break

                start += self._batch_size

        result = IngestionResult(
            batches=batches,
            discovered=discovered,
            stored=stored,
            failed=failed,
        )

        logger.info(
            (
                "Ingestion completed: batches=%d "
                "discovered=%d stored=%d failed=%d"
            ),
            result.batches,
            result.discovered,
            result.stored,
            result.failed,
        )

        return result