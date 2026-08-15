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
    Point-in-time feature set for predicting an inspection's
    final NAI, VAI or OAI classification.

    Grain:
        One row per physical inspection.

    Prediction time:
        Immediately before prediction_date.

    Important:
        Every feature must be derived only from information
        available before prediction_date.
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

    # Observation identity

    inspection_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
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

    # Prediction targets

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

    # Previous inspection

    prior_inspection_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    days_since_previous_inspection: Mapped[int | None] = (
        mapped_column(
            Integer,
            nullable=True,
        )
    )

    previous_classification: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    previous_severity: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    # Historical classifications

    prior_nai_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    prior_vai_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    prior_oai_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    prior_adverse_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Other historical regulatory events

    prior_citation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    prior_recall_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    prior_compliance_action_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Facility information

    country_area: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    product_type: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True,
    )

    # Dataset lineage

    feature_as_of_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
    )

    dataset_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
