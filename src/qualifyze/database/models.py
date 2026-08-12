import datetime

from sqlalchemy import Date, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WarningLetterRecord(Base):
    __tablename__ = "warning_letters"

    __table_args__ = (
        UniqueConstraint(
            "posted_date",
            "url",
            name="uq_warning_letter_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    url: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
        index=True,
    )

    posted_date: Mapped[datetime.date] = mapped_column(Date)
    issue_date: Mapped[datetime.date] = mapped_column(Date)

    company_name: Mapped[str] = mapped_column(String(500))
    issuing_office: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(Text)

    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    first_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )