import datetime
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sqlalchemy import Engine, text

from qualifyze.config import InspectionClassificationModelConfig
from qualifyze.services.model.inspection_classification.pipeline import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    create_inspection_classification_pipeline,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    train: pd.DataFrame
    test: pd.DataFrame
    test_start_date: datetime.date


@dataclass(frozen=True, slots=True)
class TrainingResult:
    model_version: str
    dataset_version: str
    training_rows: int
    test_rows: int
    threshold: float
    metrics: dict[str, Any]
    artifact_path: Path


class InspectionClassificationTrainingService:
    def __init__(
        self,
        *,
        engine: Engine,
        config: InspectionClassificationModelConfig,
    ) -> None:
        self._config = config
        self._engine = engine
        self._artifact_root = self._config.artifact_root

    def train(self) -> TrainingResult:
        frame = self._load_training_data()

        self._validate_training_data(frame)

        split = self._temporal_split(frame)

        logger.info(
            "Temporal split: train=%d test=%d",
            len(split.train),
            len(split.test),
        )

        pipeline = (
            create_inspection_classification_pipeline(self._config)
        )

        pipeline.fit(
            split.train[list(FEATURE_COLUMNS)],
            split.train[TARGET_COLUMN].astype(int),
        )

        test_target = split.test[
            TARGET_COLUMN
        ].astype(int)

        test_probabilities = pipeline.predict_proba(
            split.test[list(FEATURE_COLUMNS)]
        )[:, 1]

        threshold=0.5
        metrics = self._evaluate(
            target=test_target,
            probabilities=test_probabilities,
            threshold=threshold,
        )

        artifact_path = self._save_artifact(
            pipeline=pipeline,
            split=split,
            metrics=metrics,
        )

        return TrainingResult(
            model_version=self._config.model_version,
            dataset_version=self._config.dataset_version,
            training_rows=len(split.train),
            test_rows=len(split.test),
            threshold=threshold,
            metrics=metrics,
            artifact_path=artifact_path,
        )

    def _load_training_data(self) -> pd.DataFrame:
        query = text(
            """
            SELECT *
            FROM features.inspection_classification_v1
            WHERE dataset_version = :dataset_version
            ORDER BY prediction_date, inspection_id
            """
        )

        with self._engine.connect() as connection:
            frame = pd.read_sql_query(
                query,
                connection,
                params={
                    "dataset_version":
                        self._config.dataset_version,
                },
            )

        logger.info(
            "Loaded %d feature rows for dataset %s",
            len(frame),
            self._config.dataset_version,
        )

        return frame

    @staticmethod
    def _validate_training_data(
        frame: pd.DataFrame,
    ) -> None:
        required_columns = {
            "inspection_id",
            "fei_number",
            "prediction_date",
            TARGET_COLUMN,
            *FEATURE_COLUMNS,
        }

        missing_columns = (
            required_columns - set(frame.columns)
        )

        if missing_columns:
            raise ValueError(
                "Training dataset is missing columns: "
                f"{sorted(missing_columns)}"
            )

        if frame.empty:
            raise ValueError(
                "Training dataset is empty"
            )

        if frame["inspection_id"].duplicated().any():
            duplicate_examples = (
                frame.loc[
                    frame["inspection_id"].duplicated(
                        keep=False
                    ),
                    "inspection_id",
                ]
                .head(10)
                .tolist()
            )

            raise ValueError(
                "Training dataset contains duplicate "
                "inspection IDs. Examples: "
                f"{duplicate_examples}"
            )

        if frame["prediction_date"].isna().any():
            raise ValueError(
                "prediction_date contains missing values"
            )

        if frame[TARGET_COLUMN].isna().any():
            raise ValueError(
                f"{TARGET_COLUMN} contains missing values"
            )

        target_values = set(
            frame[TARGET_COLUMN]
            .astype(int)
            .unique()
        )

        if target_values != {0, 1}:
            raise ValueError(
                "Expected binary target values {0, 1}; "
                f"found {sorted(target_values)}"
            )

    @staticmethod
    def _temporal_split(
        frame: pd.DataFrame,
    ) -> TemporalSplit:
        data = frame.copy()

        data["prediction_date"] = pd.to_datetime(
            data["prediction_date"],
            errors="raise",
        )

        unique_dates = np.sort(
            data["prediction_date"].unique()
        )

        if len(unique_dates) < 10:
            raise ValueError(
                "At least 10 distinct prediction dates "
                "are required for a temporal split"
            )

        test_index = max(
            1,
            int(len(unique_dates) * 0.8),
        )

        test_index = min(
            test_index,
            len(unique_dates) - 1,
        )

        test_start = unique_dates[test_index]

        train = data.loc[
            data["prediction_date"]
            < test_start
        ].copy()

        test = data.loc[
            data["prediction_date"]
            >= test_start
        ].copy()

        for name, partition in (
            ("train", train),
            ("test", test),
        ):
            if partition.empty:
                raise ValueError(
                    f"{name} partition is empty"
                )

            classes = set(
                partition[TARGET_COLUMN]
                .astype(int)
                .unique()
            )

            if classes != {0, 1}:
                raise ValueError(
                    f"{name} partition does not contain "
                    f"both target classes: {classes}"
                )

        return TemporalSplit(
            train=train,
            test=test,
            test_start_date=pd.Timestamp(
                test_start
            ).date(),
        )

    @staticmethod
    def _evaluate(
        *,
        target: pd.Series,
        probabilities: np.ndarray,
        threshold: float,
    ) -> dict[str, Any]:
        predictions = (
            probabilities >= threshold
        ).astype(int)

        matrix = confusion_matrix(
            target,
            predictions,
            labels=[0, 1],
        )

        true_negative = int(matrix[0, 0])
        false_positive = int(matrix[0, 1])
        false_negative = int(matrix[1, 0])
        true_positive = int(matrix[1, 1])

        return {
            "roc_auc": float(
                roc_auc_score(
                    target,
                    probabilities,
                )
            ),
            "average_precision": float(
                average_precision_score(
                    target,
                    probabilities,
                )
            ),
            "brier_score": float(
                brier_score_loss(
                    target,
                    probabilities,
                )
            ),
            "accuracy": float(
                accuracy_score(
                    target,
                    predictions,
                )
            ),
            "precision": float(
                precision_score(
                    target,
                    predictions,
                    zero_division=0,
                )
            ),
            "recall": float(
                recall_score(
                    target,
                    predictions,
                    zero_division=0,
                )
            ),
            "f1": float(
                f1_score(
                    target,
                    predictions,
                    zero_division=0,
                )
            ),
            "threshold": float(threshold),
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_positive": true_positive,
            "test_adverse_rate": float(
                target.mean()
            ),
        }

    def _save_artifact(
        self,
        *,
        pipeline: Any,
        split: TemporalSplit,
        metrics: dict[str, Any],
    ) -> Path:
        trained_at = datetime.datetime.now(
            datetime.UTC
        )

        model_directory = (
            self._artifact_root
            / self._config.model_version
        )

        model_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        artifact_path = (
            model_directory / "model.joblib"
        )

        artifact = {
            "pipeline": pipeline,
            "model_name":
                "inspection-classification",
            "model_version": self._config.model_version,
            "dataset_version": self._config.dataset_version,
            "feature_columns": FEATURE_COLUMNS,
            "target_column": TARGET_COLUMN,
            "trained_at": trained_at.isoformat(),
            "test_start_date": (
                split.test_start_date.isoformat()
            ),
            "metrics": metrics,
        }

        joblib.dump(
            artifact,
            artifact_path,
        )

        metadata = {
            key: value
            for key, value in artifact.items()
            if key != "pipeline"
        }

        self._write_json(
            model_directory / "metadata.json",
            metadata,
        )

        self._write_json(
            model_directory / "metrics.json",
            metrics,
        )

        logger.info(
            "Saved model artifact to %s",
            artifact_path,
        )

        return artifact_path

    @staticmethod
    def _write_json(
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )


def main() -> None:
    from qualifyze.config import Settings
    from qualifyze.database.session import (
        create_database_engine,
    )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )

    config = Settings()  # type: ignore

    engine = create_database_engine(
        config.database
    )

    try:
        service = (
            InspectionClassificationTrainingService(
                engine=engine,
                config=config.modeling.inspection_classification
            )
        )

        result = service.train()

        logger.info(
            "Training completed: "
            "model=%s train=%d "
            "test=%d threshold=%.3f",
            result.model_version,
            result.training_rows,
            result.test_rows,
            result.threshold,
        )

        logger.info(
            "Test metrics: %s",
            json.dumps(
                result.metrics,
                sort_keys=True,
            ),
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
