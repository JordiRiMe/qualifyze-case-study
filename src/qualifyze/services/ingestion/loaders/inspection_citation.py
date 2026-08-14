import logging
from pathlib import Path

from qualifyze.services.ingestion.loaders._excel import (
    FdaExcelError,
    calculate_hash,
    optional_identifier,
    optional_text,
    read_fda_excel,
    require_columns,
    required_date,
    required_integer,
    required_text,
    row_value,
)
from qualifyze.typing import InspectionCitation

logger = logging.getLogger(__name__)


class InspectionCitationLoader:
    def __init__(self) -> None:
        self._required_columns = {
            "inspection_id": ("Inspection ID",),
            "fei_number": ("FEI Number",),
            "legal_name": ("Legal Name",),
            "inspection_end_date": (
                "Inspection End Date",
            ),
            "program_area": ("Program Area",),
            "act_cfr_number": ("Act/CFR Number",),
            "short_description": (
                "Short Description",
            ),
            "long_description": (
                "Long Description",
            ),
        }

    def load(
        self,
        path: Path,
    ) -> list[InspectionCitation]:
        frame = read_fda_excel(path)

        require_columns(
            frame,
            self._required_columns,
            filename=path.name,
        )

        citations: list[InspectionCitation] = []
        skipped_rows: list[int] = []

        for excel_row, (_, row) in enumerate(
            frame.iterrows(),
            start=2,
        ):
            try:
                act_cfr_number = optional_text(
                    row_value(row, "Act/CFR Number"),
                    null_values={"-"},
                )

                if act_cfr_number is None:
                    skipped_rows.append(excel_row)
                    continue

                values = {
                    "inspection_id": required_integer(
                        row_value(row, "Inspection ID"),
                        field="Inspection ID",
                    ),
                    "fei_number": optional_identifier(
                        row_value(row, "FEI Number")
                    ),
                    "legal_name": required_text(
                        row_value(row, "Legal Name"),
                        field="Legal Name",
                    ),
                    "inspection_end_date": required_date(
                        row_value(
                            row,
                            "Inspection End Date",
                        ),
                        field="Inspection End Date",
                    ),
                    "program_area": required_text(
                        row_value(row, "Program Area"),
                        field="Program Area",
                    ),
                    "act_cfr_number": required_text(
                        row_value(row, "Act/CFR Number"),
                        field="Act/CFR Number",
                    ),
                    "short_description": optional_text(
                        row_value(
                            row,
                            "Short Description",
                        ),
                        null_values={"-"},
                    ),
                    "long_description": optional_text(
                        row_value(
                            row,
                            "Long Description",
                        ),
                        null_values={"-"},
                    ),
                }

                values["hash"] = calculate_hash(values)

                citations.append(
                    InspectionCitation(**values)
                )
            except (TypeError, ValueError) as exc:
                raise FdaExcelError(
                    f"{path.name}, row {excel_row}: {exc}"
                ) from exc

        if skipped_rows:
            logger.warning(
                "Skipped %d citation rows without an "
                "Act/CFR Number. Example Excel rows: %s",
                len(skipped_rows),
                skipped_rows[:10],
            )

        return citations