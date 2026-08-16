import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from qualifyze.services.features.inspection_classification import (
    InspectionClassificationFeatureBuilder,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FeatureBuildResult:
    inspection_classification: int

    @property
    def total(self) -> int:
        return self.inspection_classification


class FeatureBuildService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        inspection_classification_builder:
            InspectionClassificationFeatureBuilder,
    ) -> None:
        self._session_factory = session_factory
        self._inspection_classification_builder = (
            inspection_classification_builder
        )

    def build_all(
        self,
        *,
        dataset_version: str,
    ) -> FeatureBuildResult:
        # All feature tables see the same source-data state,
        # and all succeed or all are rolled back.
        with self._session_factory.begin() as session:
            classification_count = (
                self._inspection_classification_builder.build(
                    session=session,
                    dataset_version=dataset_version,
                )
            )

        return FeatureBuildResult(
            inspection_classification=classification_count,
        )


def create_feature_build_service(
    session_factory: sessionmaker[Session],
) -> FeatureBuildService:
    return FeatureBuildService(
        session_factory=session_factory,
        inspection_classification_builder=(
            InspectionClassificationFeatureBuilder()
        ),
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
        service = create_feature_build_service(
            session_factory
        )

        result = service.build_all(
            dataset_version="classification-v1",
        )

        logger.info(
            "Feature build completed: %d rows",
            result.inspection_classification,
        )
    finally:
        engine.dispose()
