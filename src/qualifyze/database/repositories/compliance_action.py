from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.database.models.core.compliance_action import ComplianceActionRecord
from qualifyze.database.repositories import _batched
from qualifyze.typing import ComplianceAction


class ComplianceActionRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _values(
        action: ComplianceAction,
    ) -> dict[str, object]:
        return {
            "fei_number": action.fei_number,
            "legal_name": action.legal_name,
            "state": action.state,
            "country_area": action.country_area,
            "product_type": action.product_type,
            "action_taken_date":
                action.action_taken_date,
            "action_type": action.action_type,
            "case_injunction_id":
                action.case_injunction_id,
            "hash": action.hash,
        }

    def upsert(self, action: ComplianceAction) -> None:
        with self._session_factory.begin() as session:
            self.upsert_many(
                session=session,
                actions=[action],
            )

    def upsert_many(
        self,
        session: Session,
        actions: Sequence[ComplianceAction],
    ) -> int:
        if not actions:
            return 0

        for batch in _batched(actions, size=1000):
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
            
        return len(actions)
