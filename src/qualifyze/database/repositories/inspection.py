from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from qualifyze.database.models.inspection import InspectionRecord
from qualifyze.database.repositories import _batched
from qualifyze.typing import Inspection


class InspectionRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _values(inspection: Inspection) -> dict[str, object]:
        return {
            "inspection_id": inspection.inspection_id,
            "fei_number": inspection.fei_number,
            "legal_name": inspection.legal_name,
            "city": inspection.city,
            "state": inspection.state,
            "zip_code": inspection.zip_code,
            "country": inspection.country,
            "inspection_end_date":
                inspection.inspection_end_date,
            "fiscal_year": inspection.fiscal_year,
            "posted_citations": inspection.posted_citations,
            "classification": inspection.classification,
            "classification_code":
                inspection.classification_code,
            "project_area": inspection.project_area,
            "product_type": inspection.product_type,
            "additional_details":
                inspection.additional_details,
            "fmd_145_date": inspection.fmd_145_date,
            "hash": inspection.hash,
        }


    def upsert(self, inspection: Inspection) -> None:
        with self._session_factory.begin() as session:
            self.upsert_many(
                session=session,
                inspections=[inspection],
            )

    def upsert_many(
        self,
        session: Session,
        inspections: Sequence[Inspection],
    ) -> int:
        if not inspections:
            return 0

        for batch in _batched(inspections, size=1000):
            values = [
                self._values(inspection)
                for inspection in batch
            ]

            statement = insert(InspectionRecord).values(values)

            statement = statement.on_conflict_do_update(
                constraint="uq_fda_inspection_identity",
                set_= {
                    "fei_number":
                        statement.excluded.fei_number,
                    "legal_name":
                        statement.excluded.legal_name,
                    "city": statement.excluded.city,
                    "state": statement.excluded.state,
                    "zip_code":
                        statement.excluded.zip_code,
                    "country": statement.excluded.country,
                    "inspection_end_date":
                        statement.excluded.inspection_end_date,
                    "fiscal_year":
                        statement.excluded.fiscal_year,
                    "posted_citations":
                        statement.excluded.posted_citations,
                    "classification":
                        statement.excluded.classification,
                    "classification_code":
                        statement.excluded.classification_code,
                    "product_type":
                        statement.excluded.product_type,
                    "additional_details":
                        statement.excluded.additional_details,
                    "fmd_145_date":
                        statement.excluded.fmd_145_date,
                    "hash": statement.excluded.hash,
                    "last_seen_at": func.now(),
                },
            )

            session.execute(statement)

        return len(inspections)
