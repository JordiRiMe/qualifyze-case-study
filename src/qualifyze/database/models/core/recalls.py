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


class RecallRecord(Base):
    __tablename__ = "recalls"

    __table_args__ = (
        UniqueConstraint(
            "fei_number",   
            "event_id",
            "product_id",
            name="uq_fda_recall_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

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

    product_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    product_classification: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    distribution_partner: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    recalling_firm_city: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    recalling_firm_state: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    recalling_firm_country: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    center_classification_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    reason_recall: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )
    product_description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    event_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    event_classification: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    center: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    recall_details: Mapped[str | None] = mapped_column(
        String(255),
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
