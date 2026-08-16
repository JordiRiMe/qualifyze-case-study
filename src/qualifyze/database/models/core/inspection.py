import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from qualifyze.database import Base


class InspectionRecord(Base):
    __tablename__ = "inspections"

    __table_args__ = (
        UniqueConstraint(
            "inspection_id",
            "project_area",
            "product_type",
            "additional_details",
            name="uq_fda_inspection_identity",
        ),
        CheckConstraint(
            """
            classification_code IS NULL
            OR classification_code IN ('NAI', 'VAI', 'OAI')
            """,
            name="ck_fda_inspection_classification",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    inspection_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    fei_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )
    city: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    state: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    zip_code: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    country: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    inspection_end_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    fiscal_year: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
    )

    posted_citations: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    classification: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    classification_code: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        index=True,
    )

    project_area: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    product_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    additional_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    fmd_145_date: Mapped[datetime.date | None] = mapped_column(
        Date,
        nullable=True,
    )

    hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    first_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
