import datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from qualifyze.database import Base


class ComplianceActionRecord(Base):
    __tablename__ = "compliance_actions"

    __table_args__ = (
        UniqueConstraint(
            "case_injunction_id",
            "fei_number",
            "product_type",
            name="uq_fda_compliance_action_identity",
        ),
        CheckConstraint(
            """
            action_type IN (
                'Warning Letter',
                'Injunction',
                'Seizure'
            )
            """,
            name="ck_fda_compliance_action_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    fei_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    legal_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    country_area: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    product_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    action_taken_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    case_injunction_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
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
