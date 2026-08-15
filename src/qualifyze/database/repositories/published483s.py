from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.database.models.published483s import Published483Record
from qualifyze.database.repositories import _batched
from qualifyze.typing import Published483


class Published483sRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _values(
        published483: Published483,
    ) -> dict[str, object]:
        return {
            "fei_number": published483.fei_number,
            "legal_name": published483.legal_name,
            "record_date": published483.record_date,
            "record_type": published483.record_type,
            "publish_date": published483.publish_date,
            "download": published483.download,
            "record_id": published483.record_id,
            "hash": published483.hash,
        }

    def upsert(self, recall: Published483) -> None:
        with self._session_factory.begin() as session:
            self.upsert_many(
                session=session,
                recalls=[recall],
            )

    def upsert_many(
        self,
        session: Session,
        recalls: Sequence[Published483],
    ) -> int:
        if not recalls:
            return 0

        for batch in _batched(recalls, size=1000):
            values = [
                self._values(inspection)
                for inspection in batch
            ]

            statement = insert(Published483Record).values(values)

            statement = statement.on_conflict_do_update(
                constraint="uq_fda_published483_identity", 
                set_ = {
                    "fei_number": statement.excluded.fei_number,
                    "legal_name": statement.excluded.legal_name,
                    "record_date": statement.excluded.record_date,
                    "record_type": statement.excluded.record_type,
                    "publish_date": statement.excluded.publish_date,
                    "download": statement.excluded.download,
                    "record_id": statement.excluded.record_id,
                    "hash": statement.excluded.hash,
                    "last_seen_at": func.now(),
                },
            )

            session.execute(statement)
            
        return len(recalls)
