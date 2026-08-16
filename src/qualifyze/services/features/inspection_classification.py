import argparse
import datetime
import logging
from datetime import UTC
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FeatureBuildError(RuntimeError):
    """Raised when a feature snapshot cannot be built."""


class InspectionClassificationFeatureBuilder:
    _sql_path = (
        Path(__file__).parents[2]
        / "database"
        / "sql"
        / "inspection_classification.sql"
    )

    def build(
        self,
        *,
        session: Session,
        dataset_version,
    ) -> int:
        normalized_version = dataset_version.strip()

        if not normalized_version:
            raise ValueError(
                "dataset_version cannot be empty"
            )
        
        sql = self._sql_path.read_text(
            encoding="utf-8"
        )

        # One active, completely refreshed dataset.
        session.execute(
            text(
                """
                TRUNCATE TABLE
                features.inspection_classification_v1
                """
            ),
            {
                "dataset_version": normalized_version,
            },
        )

        inserted_count = session.execute(
            text(sql),
            {
                "dataset_version": normalized_version,
            },
        ).scalar_one()

        self._validate_snapshot(
            session=session,
            dataset_version=normalized_version,
            expected_count=inserted_count,
        )

        return inserted_count

    @staticmethod
    def _validate_snapshot(
        *,
        session: Session,
        dataset_version: str,
        expected_count: int,
    ) -> None:
        result = session.execute(
            text(
                """
                SELECT
                    COUNT(*)::INTEGER AS row_count,

                    COUNT(
                        DISTINCT inspection_id
                    )::INTEGER AS inspection_count,

                    COUNT(*) FILTER (
                        WHERE target_classification
                            NOT IN ('NAI', 'VAI', 'OAI')
                           OR target_classification IS NULL
                    )::INTEGER AS invalid_targets,

                    COUNT(*) FILTER (
                        WHERE prior_inspection_count < 0
                    )::INTEGER AS invalid_history,

                    COUNT(*) FILTER (
                        WHERE prior_inspection_count = 0
                          AND (
                              is_first_observed_inspection
                                    IS DISTINCT FROM 1
                                OR previous_classification_adverse
                                    IS DISTINCT FROM 0
                                OR days_since_previous_inspection
                                    IS DISTINCT FROM 0
                          )
                    )::INTEGER AS invalid_cold_start

                FROM features.inspection_classification_v1

                WHERE dataset_version = :dataset_version
                """
            ),
            {
                "dataset_version": dataset_version,
            },
        ).one()

        problems: list[str] = []

        if result.row_count != expected_count:
            problems.append(
                "stored row count does not match "
                "inserted row count"
            )

        if result.row_count != result.inspection_count:
            problems.append(
                "feature snapshot contains duplicate "
                "inspection IDs"
            )

        if result.invalid_targets:
            problems.append(
                f"{result.invalid_targets} target labels "
                "are invalid"
            )

        if result.invalid_history:
            problems.append(
                f"{result.invalid_history} history counts "
                "are invalid"
            )

        if result.invalid_cold_start:
            problems.append(
                f"{result.invalid_cold_start} cold-start "
                "rows contain previous-inspection values"
            )

        if problems:
            raise FeatureBuildError("; ".join(problems))

def parse_date(value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date {value!r}; expected YYYY-MM-DD"
        ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the inspection-classification "
            "feature dataset."
        ),
    )

    parser.add_argument(
        "--cutoff-date",
        type=parse_date,
        default=datetime.datetime.now(tz=UTC).date(),
        help=(
            "Latest inspection date included in the "
            "snapshot, in YYYY-MM-DD format. "
            "Default: 2025-12-31."
        ),
    )

    parser.add_argument(
        "--dataset-version",
        default="classification-v1",
        help=(
            "Logical feature dataset version. "
            "Default: classification-v1."
        ),
    )

    return parser.parse_args()


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

    args = parse_args()
    config = Settings()  # type: ignore

    engine = create_database_engine(
        config.database
    )

    try:
        # SQLAlchemy will create tables inside the schema,
        # but it does not necessarily create the schema itself.
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE SCHEMA IF NOT EXISTS features"
                )
            )

        create_database_tables(engine)

        session_factory = create_session_factory(
            engine
        )

        builder = (
            InspectionClassificationFeatureBuilder()
        )

        logger.info(
            "Starting feature build: "
            "version=%s",
            args.dataset_version,
        )

        # build() deletes, inserts and validates the snapshot.
        # Any exception causes the transaction to roll back.
        with session_factory.begin() as session:
            inserted_count = builder.build(
                session=session,
                dataset_version=args.dataset_version,
            )

        logger.info(
            "Feature build completed: "
            "version=%s rows=%d",
            args.dataset_version,
            inserted_count,
        )

    except Exception:
        logger.exception(
            "Inspection-classification feature "
            "build failed"
        )
        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
