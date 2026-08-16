import datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from qualifyze.database import Base


class InspectionCitationRecord(Base):
    __tablename__ = "inspections_citations"

    __table_args__ = (
        UniqueConstraint(
            "inspection_id",
            "program_area",
            "act_cfr_number",
            "short_description",
            "long_description",
            name="uq_fda_inspection_citation_identity",
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

    legal_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    inspection_end_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    program_area: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    act_cfr_number: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    short_description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    long_description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    first_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
