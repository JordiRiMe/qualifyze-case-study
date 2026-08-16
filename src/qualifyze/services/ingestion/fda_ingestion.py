import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from qualifyze.config import FDAIngestionConfig
from qualifyze.database.repositories.compliance_action import (
    ComplianceActionRepository,
)
from qualifyze.database.repositories.inspection import (
    InspectionRepository,
)
from qualifyze.database.repositories.inspection_citation import (
    InspectionCitationRepository,
)
from qualifyze.database.repositories.recalls import (
    RecallsRepository,
)
from qualifyze.database.repositories.published483s import(
    Published483sRepository,
)
from qualifyze.services.ingestion.loaders.compliance_action import (
    ComplianceActionLoader,
)
from qualifyze.services.ingestion.loaders.inspection import (
    InspectionLoader,
)
from qualifyze.services.ingestion.loaders.inspection_citation import (
    InspectionCitationLoader,
)
from qualifyze.services.ingestion.loaders.published483s import (
    Published483Loader,
)
from qualifyze.services.ingestion.loaders.recalls import (
    RecallsLoader,
)

from qualifyze.typing import (
    ComplianceAction,
    Inspection,
    InspectionCitation,
    Published483,
    Recall,
)

logger = logging.getLogger(__name__)


DEFAULT_FDA_DATA_DIRECTORY = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "fda"
)

@dataclass(frozen=True, slots=True)
class FdaIngestionResult:
    inspections: int
    citations: int
    compliance_actions: int
    recalls: int
    published483s: int

    @property
    def total(self) -> int:
        return (
            self.inspections
            + self.citations
            + self.compliance_actions
            + self.recalls
            + self.published483s
        )


class DuplicateRecordsError(ValueError):
    pass


class FdaIngestionService:
    def __init__(
        self,
        config: FDAIngestionConfig,
        session_factory: sessionmaker[Session],
        inspections_loader: InspectionLoader,
        citations_loader: InspectionCitationLoader,
        actions_loader: ComplianceActionLoader,
        publised483s_loader: Published483Loader,
        recalls_loader: RecallsLoader,
        inspection_repository: InspectionRepository,
        citation_repository: InspectionCitationRepository,
        compliance_repository: ComplianceActionRepository,
        published483s_repository: Published483sRepository,
        recalls_repository: RecallsRepository,
    ) -> None:
        self._config = config
        self._session_factory = session_factory

        self._inspections_loader = inspections_loader
        self._citations_loader = citations_loader
        self._actions_loader = actions_loader
        self._published483s_loader = publised483s_loader
        self._recalls_loader = recalls_loader

        self._inspection_repository = inspection_repository
        self._citation_repository = citation_repository
        self._compliance_repository = compliance_repository
        self._published483s_repository = published483s_repository
        self._recalls_repository = recalls_repository

    def ingest_all(
        self,
        data_directory: Path,
    ) -> FdaIngestionResult:
        files = self._resolve_files(data_directory)

        # Load and validate everything before opening a database transaction.
        inspections = self._inspections_loader.load(
            files.inspections,
        )
        citations = self._citations_loader.load(
            files.citations,
        )
        actions = self._actions_loader.load(
            files.compliance_actions,
        )
        published483s = self._published483s_loader.load(
            files.published483s,
        )
        recalls = self._recalls_loader.load(
            files.recalls,
        )

        self._validate_records(
            inspections=inspections,
            citations=citations,
            actions=actions,
            published483s=published483s,
            recalls=recalls,
        )

        # All three upserts succeed or all three are rolled back.
        with self._session_factory.begin() as session:
            inspection_count = (
                self._inspection_repository.upsert_many(
                    session,
                    inspections,
                )
            )
            citation_count = (
                self._citation_repository.upsert_many(
                    session,
                    citations,
                )
            )
            action_count = (
                self._compliance_repository.upsert_many(
                    session,
                    actions,
                )
            )
            published483s_count = (
                self._published483s_repository.upsert_many(
                    session,
                    published483s,
                )
            )
            recalls_count = (
                self._recalls_repository.upsert_many(
                    session,
                    recalls,
                )
            )

        return FdaIngestionResult(
            inspections=inspection_count,
            citations=citation_count,
            compliance_actions=action_count,
            published483s=published483s_count,
            recalls=recalls_count,
        )

    def _resolve_files(
        self,
        data_directory: Path,
    ) -> "FdaIngestionFiles":
        data_directory = data_directory.resolve()

        if not data_directory.is_dir():
            raise NotADirectoryError(
                f"FDA data directory does not exist: {data_directory}"
            )

        files = FdaIngestionFiles(
            inspections=data_directory / self._config.files.inspections,
            citations=(
                data_directory / self._config.files.citations
            ),
            compliance_actions=(
                data_directory / self._config.files.compliance_actions
            ),
            published483s=(
                data_directory / self._config.files.published483s
            ),
            recalls=(
                data_directory / self._config.files.recalls
            )
        )

        missing_files = [
            path
            for path in (
                files.inspections,
                files.citations,
                files.compliance_actions,
                files.recalls,
                files.published483s,
            )
            if not path.is_file()
        ]

        if missing_files:
            formatted = ", ".join(
                str(path) for path in missing_files
            )
            raise FileNotFoundError(
                f"Missing FDA input files: {formatted}"
            )

        return files

    @staticmethod
    def _validate_records(
        *,
        inspections: Sequence[Inspection],
        citations: Sequence[InspectionCitation],
        actions: Sequence[ComplianceAction],
        published483s: Sequence[Published483],
        recalls: Sequence[Recall],
    ) -> None:
        _raise_on_duplicates(
            records=inspections,
            key=lambda record: (
                record.inspection_id,
                record.project_area,
                record.product_type,
                record.additional_details,
            ),
            dataset="inspections",
        )

        _raise_on_duplicates(
            records=citations,
            key=lambda record: (
                record.inspection_id,
                record.program_area,
                record.act_cfr_number,
                record.short_description,
                record.long_description,
            ),
            dataset="inspection citations",
        )

        _raise_on_duplicates(
            records=actions,
            key=lambda record: (
                record.case_injunction_id,
                record.fei_number,
                record.product_type,
            ),
            dataset="compliance actions",
        )

        _raise_on_duplicates(
            records=published483s,
            key=lambda record: (
                record.record_id,
                record.fei_number,
            ),
            dataset="published 483s",
        )

        _raise_on_duplicates(
            records=recalls,
            key=lambda record: (
                record.event_id,
                record.product_id,
                record.fei_number,
            ),
            dataset="recalls",
        )


@dataclass(frozen=True, slots=True)
class FdaIngestionFiles:
    inspections: Path
    citations: Path
    compliance_actions: Path
    published483s: Path
    recalls: Path


def _raise_on_duplicates[T, K](
    *,
    records: Sequence[T],
    key: Callable[[T], K],
    dataset: str,
) -> None:
    seen: set[K] = set()
    duplicates: set[K] = set()

    for record in records:
        record_key = key(record)

        if record_key in seen:
            duplicates.add(record_key)

        seen.add(record_key)

    if duplicates:
        examples = list(duplicates)[:10]

        raise DuplicateRecordsError(
            f"Found {len(duplicates)} duplicate identities "
            f"in {dataset}. Examples: {examples}"
        )

def create_fda_ingestion_service(
    config: FDAIngestionConfig,
    session_factory: sessionmaker[Session],
) -> FdaIngestionService:
    return FdaIngestionService(
        config=config,
        session_factory=session_factory,
        inspections_loader=InspectionLoader(),
        citations_loader=InspectionCitationLoader(),
        actions_loader=ComplianceActionLoader(),
        publised483s_loader=Published483Loader(),
        recalls_loader=RecallsLoader(),
        inspection_repository=InspectionRepository(
            session_factory=session_factory,
        ),
        citation_repository=InspectionCitationRepository(
            session_factory=session_factory,
        ),
        compliance_repository=ComplianceActionRepository(
            session_factory=session_factory,
        ),
        published483s_repository=Published483sRepository(
            session_factory=session_factory,
        ),
        recalls_repository=RecallsRepository(
            session_factory=session_factory,
        )
    )


def run_fda_ingestion(
    config: FDAIngestionConfig,
    session_factory: sessionmaker[Session],
    data_directory: Path = DEFAULT_FDA_DATA_DIRECTORY,
) -> FdaIngestionResult:
    service = create_fda_ingestion_service(
        config=config,
        session_factory=session_factory,
    )

    return service.ingest_all(
        data_directory=data_directory,
    )

def main() -> None:
    from qualifyze.config import Settings
    from qualifyze.database.session import (
        create_database_engine,
        create_database_tables,
        create_session_factory,
    )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )

    config = Settings()  # type: ignore
    engine = create_database_engine(config.database)
    create_database_tables(engine)
    session_factory = create_session_factory(engine)

    try:
        result = run_fda_ingestion(
            config=config.fda_ingestion,
            session_factory=session_factory,
        )

        logger.info("FDA ingestion completed")
        logger.info(f"Inspections processed: {result.inspections}")
        logger.info(f"Citations processed: {result.citations}")
        logger.info(
            "Compliance actions processed: "
            f"{result.compliance_actions}"
        )
        logger.info(f"Total records processed: {result.total}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()