from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.database.models.core.inspection_citation import InspectionCitationRecord
from qualifyze.database.repositories import _batched
from qualifyze.typing import InspectionCitation


class InspectionCitationRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _values(
        citation: InspectionCitation,
    ) -> dict[str, object]:
        return {
            "inspection_id": citation.inspection_id,
            "fei_number": citation.fei_number,
            "legal_name": citation.legal_name,
            "inspection_end_date":
                citation.inspection_end_date,
            "program_area": citation.program_area,
            "act_cfr_number": citation.act_cfr_number,
            "short_description":
                citation.short_description,
            "long_description":
                citation.long_description,
            "hash": citation.hash,
        }

    def upsert(self, citation: InspectionCitation) -> None:
        with self._session_factory.begin() as session:
            self.upsert_many(
                session=session,
                citations=[citation],
            )

    def upsert_many(
        self,
        session: Session,
        citations: Sequence[InspectionCitation],
    ) -> int:
        if not citations:
            return 0

        for batch in _batched(citations, size=1000):
            values = [
                self._values(inspection)
                for inspection in batch
            ]

            statement = insert(InspectionCitationRecord).values(values)

            statement = statement.on_conflict_do_update(
                constraint="uq_fda_inspection_citation_identity", 
                set_ = {
                    "fei_number":
                        statement.excluded.fei_number,
                    "legal_name":
                        statement.excluded.legal_name,
                    "inspection_end_date":
                        statement.excluded.inspection_end_date,
                    "program_area":
                        statement.excluded.program_area,
                    "short_description":
                        statement.excluded.short_description,
                    "long_description":
                        statement.excluded.long_description,
                    "hash": statement.excluded.hash,
                    "last_seen_at": func.now(),
                },
            )

            session.execute(statement)

        return len(citations)
