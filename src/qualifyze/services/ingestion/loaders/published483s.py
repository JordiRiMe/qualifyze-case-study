from pathlib import Path

from qualifyze.services.ingestion.loaders._excel import (
    FdaExcelError,
    calculate_hash,
    optional_identifier,
    read_fda_excel,
    require_columns,
    required_date,
    required_identifier,
    required_text,
    row_value,
)
from qualifyze.typing import Published483


class Published483Loader:
    def __init__(self) -> None:
        self._required_columns = {
            "fei_number": ("FEI Number",),
            "legal_name": ("Legal Name",),
            "record_date": ("Record Date",),
            "record_type": ("Record Type",),
            "publish_date": ("Publish Date",),
            "download": ("Download",),
            "record_id": ("Record ID",),
        }

    def load(
        self,
        path: Path,
    ) -> list[Published483]:
        frame = read_fda_excel(path)

        require_columns(
            frame,
            self._required_columns,
            filename=path.name,
        )

        published483s: list[Published483] = []
        skipped_rows: list[int] = []

        for excel_row, (_, row) in enumerate(
            frame.iterrows(),
            start=2,
        ):
            fei_number = optional_identifier(
                row_value(
                    row,
                    "FEI Number",
                    "FEI",
                )
            )
            if fei_number is None:
                skipped_rows.append(excel_row)
                continue

            try:
                values = {
                    "fei_number": optional_identifier(
                        row_value(row, "FEI Number"),
                    ),
                    "legal_name": required_text(
                        row_value(row, "Legal Name"),
                        field="Legal Name",
                    ),
                    "record_date": required_date(
                        row_value(row, "Record Date"),
                        field="Record Date",
                    ),
                    "record_type": required_text(
                        row_value(row, "Record Type"),
                        field="Record Type"
                    ),
                    "publish_date": required_date(
                        row_value(row, "Publish Date"),
                        field="Publish Date",
                    ),
                    "download": required_text(
                        row_value(row, "Download"),
                        field="Download"
                    ),
                    "record_id": required_identifier(
                        row_value(row, "Record ID"),
                        field="Record ID",
                    ),
                }

                values["hash"] = calculate_hash(values)

                published483s.append(
                    Published483(**values)
                )
            except (TypeError, ValueError) as exc:
                raise FdaExcelError(
                    f"{path.name}, row {excel_row}: {exc}"
                ) from exc

        return published483s
