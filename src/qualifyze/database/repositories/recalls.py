from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.database.models.compliance_action import ComplianceActionRecord
from qualifyze.database.repositories import _batched
from qualifyze.typing import Recall


class ComplianceActionRepository:
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
                self._values(inspection)
                for inspection in batch
            ]

            statement = insert(ComplianceActionRecord).values(values)

            statement = statement.on_conflict_do_update(
                constraint="uq_fda_compliance_action_identity", 
                set_ = {
                    "legal_name":
                        statement.excluded.legal_name,
                    "state": statement.excluded.state,
                    "country_area":
                        statement.excluded.country_area,
                    "product_type":
                        statement.excluded.product_type,
                    "action_taken_date":
                        statement.excluded.action_taken_date,
                    "action_type":
                        statement.excluded.action_type,
                    "hash": statement.excluded.hash,
                    "last_seen_at": func.now(),
                },
            )

            session.execute(statement)
            
        return len(recalls)
