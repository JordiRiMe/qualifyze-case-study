from typing import Final

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
)

from qualifyze.config import InspectionClassificationModelConfig

IDENTIFIER_COLUMNS: Final[tuple[str, ...]] = (
    "inspection_id",
    "fei_number",
    "prediction_date",
)

CONTINUOUS_FEATURES: Final[tuple[str, ...]] = (
    "prior_inspection_count",
    "days_since_previous_inspection",
    "historical_product_type_count",
    "prior_citation_count",
    "previous_inspection_citation_count",
    "prior_citations_per_inspection",
    "repeated_cfr_count",
    "prior_published_483_count_per_inspection",
    "prior_warning_letter_count_per_inspection",
    "prior_recall_event_count_per_inspection",
)

BINARY_FEATURES: Final[tuple[str, ...]] = (
    "is_first_observed_inspection",
    "previous_classification_adverse",
    "has_prior_product_food",
    "has_prior_product_drug",
    "has_prior_product_device",
    "has_prior_product_biologic",
    "has_prior_product_veterinary",
    "has_prior_product_tobacco",
    "has_prior_product_other",
)

CATEGORICAL_FEATURES: Final[tuple[str, ...]] = (
    "state",
)

FEATURE_COLUMNS: Final[tuple[str, ...]] = (
    CONTINUOUS_FEATURES
    + BINARY_FEATURES
    + CATEGORICAL_FEATURES
)

TARGET_COLUMN: Final[str] = "target_adverse"


def create_inspection_classification_pipeline(
    config: InspectionClassificationModelConfig,
) -> Pipeline:
    continuous_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="constant",
                    fill_value=0,
                ),
            ),
            # (
            #     "scaler",
            #     StandardScaler(),
            # ),
        ],
    )

    binary_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="constant",
                    fill_value=0,
                ),
            ),
        ],
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="constant",
                    fill_value="UNKNOWN",
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    drop="first",
                ),
            ),
        ],
    )

    processor = ColumnTransformer(
        transformers=[
            (
                "continuous",
                continuous_pipeline,
                CONTINUOUS_FEATURES,
            ),
            (
                "binary",
                binary_pipeline,
                BINARY_FEATURES,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ],
    )

    classifier = LogisticRegression(
        solver="newton-cholesky",
        C=0.1,
        max_iter=config.maximum_iterations,
        random_state=config.random_state,
    )

    return Pipeline(
        steps=[
            (
                "feature_processing",
                processor,
            ),
            (
                "classifier",
                classifier,
            ),
        ],
    )
