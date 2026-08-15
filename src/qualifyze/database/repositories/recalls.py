from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.database.models.recalls import RecallRecord
from qualifyze.database.repositories import _batched
from qualifyze.typing import Recall


class RecallsRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _values(
        recall: Recall,
    ) -> dict[str, object]:
        return {
            "fei_number": recall.fei_number,
            "legal_name": recall.legal_name,
            "product_type": recall.product_type,
            "product_classification": recall.product_classification,
            "status": recall.status,
            "distribution_partner": recall.distribution_partner,
            "recalling_firm_city": recall.recalling_firm_city,
            "recalling_firm_state": recall. recalling_firm_state,
            "recalling_firm_country": recall.recalling_firm_country,
            "center_classification_date": recall.center_classification_date,
            "reason_recall": recall.reason_recall,
            "product_description": recall.product_description,
            "event_id": recall.event_id,
            "event_classification": recall.event_classification,
            "product_id": recall.product_id,
            "center": recall.center,
            "recall_details": recall.recall_details,
            "hash": recall.hash,
        }

    def upsert(self, recall: Recall) -> None:
        with self._session_factory.begin() as session:
            self.upsert_many(
                session=session,
                recalls=[recall],
            )

    def upsert_many(
        self,
        session: Session,
        recalls: Sequence[Recall],
    ) -> int:
        if not recalls:
            return 0

        for batch in _batched(recalls, size=1000):
            values = [
                self._values(recall)
                for recall in batch
            ]

            statement = insert(RecallRecord).values(values)

            statement = statement.on_conflict_do_update(
                constraint="uq_fda_recall_identity", 
                set_ = {
                    "fei_number": statement.excluded.fei_number,
                    "legal_name": statement.excluded.legal_name,
                    "product_type": statement.excluded.product_type,
                    "product_classification": statement.excluded.product_classification,
                    "status": statement.excluded.status,
                    "distribution_partner": statement.excluded.distribution_partner,
                    "recalling_firm_city": statement.excluded.recalling_firm_city,
                    "recalling_firm_state": statement.excluded.recalling_firm_state,
                    "recalling_firm_country": statement.excluded.recalling_firm_country,
                    "center_classification_date": statement.excluded.center_classification_date,
                    "reason_recall": statement.excluded.reason_recall,
                    "product_description": statement.excluded.product_description,
                    "event_id": statement.excluded.event_id,
                    "event_classification": statement.excluded.event_classification,
                    "product_id": statement.excluded.product_id,
                    "center": statement.excluded.center,
                    "recall_details": statement.excluded.recall_details,
                    "hash": statement.excluded.hash,
                    "last_seen_at": func.now(),
                },
            )

            session.execute(statement)
            
        return len(recalls)
