import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from qualifyze.database import Base


class InspectionClassificationFeature(Base):
    """
    Point-in-time features for predicting whether an inspection
    receives NAI, VAI or OAI.

    Grain:
        One row per physical inspection.

    Prediction date:
        Currently represented by inspection_end_date.

    History:
        Features use only events dated before prediction_date.
    """

    __tablename__ = "inspection_classification_v1"

    __table_args__ = (
        CheckConstraint(
            "target_classification IN ('NAI', 'VAI', 'OAI')",
            name="ck_inspection_feature_target_classification",
        ),
        CheckConstraint(
            "target_severity BETWEEN 0 AND 2",
            name="ck_inspection_feature_target_severity",
        ),
        CheckConstraint(
            "prior_inspection_count >= 0",
            name="ck_inspection_feature_prior_count",
        ),
        CheckConstraint(
            "is_first_observed_inspection IN (0, 1)",
            name="ck_inspection_feature_first_observed",
        ),
        CheckConstraint(
            """
            previous_classification_adverse IS NULL
            OR previous_classification_adverse IN (0, 1)
            """,
            name="ck_inspection_feature_previous_adverse",
        ),
        CheckConstraint(
            """
            (
                target_classification = 'NAI'
                AND target_severity = 0
                AND target_adverse = false
            )
            OR
            (
                target_classification = 'VAI'
                AND target_severity = 1
                AND target_adverse = true
            )
            OR
            (
                target_classification = 'OAI'
                AND target_severity = 2
                AND target_adverse = true
            )
            """,
            name="ck_inspection_feature_target_consistency",
        ),
        Index(
            "ix_inspection_feature_fei_prediction_date",
            "fei_number",
            "prediction_date",
        ),
        Index(
            "ix_inspection_feature_target_date",
            "target_classification",
            "prediction_date",
        ),
        {"schema": "features"},
    )

    # Identity

    inspection_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    dataset_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    fei_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    prediction_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    # Target

    target_classification: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        index=True,
    )

    target_severity: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    target_adverse: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    # Inspection history

    prior_inspection_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_first_observed_inspection: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    days_since_previous_inspection: Mapped[int | None] = (
        mapped_column(
            Integer,
            nullable=False,
        )
    )

    previous_classification_adverse: Mapped[int | None] = (
        mapped_column(
            SmallInteger,
            nullable=False,
        )
    )

    # Product history
    historical_product_type_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    has_prior_product_food: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    has_prior_product_drug: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    has_prior_product_device: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    has_prior_product_biologic: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    has_prior_product_veterinary: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    has_prior_product_tobacco: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    has_prior_product_other: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    # Citation history

    prior_citation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    previous_inspection_citation_count: Mapped[int] = (
        mapped_column(
            Integer,
            nullable=False,
        )
    )

    prior_citations_per_inspection: Mapped[float] = (
        mapped_column(
            Float,
            nullable=False,
        )
    )

    repeated_cfr_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Geography

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Published Form 483 history

    prior_published_483_count_per_inspection: Mapped[float] = (
        mapped_column(
            Float,
            nullable=False,
        )
    )

    # Warning-letter history

    prior_warning_letter_count_per_inspection: Mapped[float] = (
        mapped_column(
            Float,
            nullable=False,
        )
    )

    # Recall history

    prior_recall_event_count_per_inspection: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Lineage

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )