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


class Published483Record(Base):
    __tablename__ = "published483"

    __table_args__ = (
        UniqueConstraint(
            "record_id",   
            "fei_number",
            name="uq_fda_published483_identity",
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

    record_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    record_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    publish_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    download: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    record_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
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
