from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.database.models.warning_letter import WarningLetterRecord
from qualifyze.typing import WarningLetter


class WarningLetterRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def upsert(self, letter: WarningLetter) -> None:
        values = {
            "url": letter.url,
            "posted_date": letter.posted_date,
            "issue_date": letter.issue_date,
            "company_name": letter.company_name,
            "issuing_office": letter.issuing_office,
            "subject": letter.subject,
            "title": letter.title,
            "content": letter.content,
            "hash": letter.hash,
        }

        statement = insert(WarningLetterRecord).values(**values)

        statement = statement.on_conflict_do_update(
            index_elements=[WarningLetterRecord.url],
            set_={
                "posted_date": statement.excluded.posted_date,
                "issue_date": statement.excluded.issue_date,
                "company_name": statement.excluded.company_name,
                "issuing_office": statement.excluded.issuing_office,
                "subject": statement.excluded.subject,
                # Do not erase existing details when saving a summary.
                "title": func.coalesce(
                    statement.excluded.title,
                    WarningLetterRecord.title,
                ),
                "content": func.coalesce(
                    statement.excluded.content,
                    WarningLetterRecord.content,
                ),
                "last_seen_at": func.now(),
            },
        )

        with self._session_factory.begin() as session:
            session.execute(statement)

    def find_existing_urls(
        self,
        urls: Iterable[str],
    ) -> set[str]:
        unique_urls = tuple(set(urls))

        if not unique_urls:
            return set()

        with self._session_factory() as session:
            statement = select(
                WarningLetterRecord.url
            ).where(
                WarningLetterRecord.url.in_(unique_urls)
            )

            return set(session.scalars(statement).all())