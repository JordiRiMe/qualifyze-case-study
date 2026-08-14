from pathlib import Path

from qualifyze.services.ingestion.loaders._excel import (
    FdaExcelError,
    calculate_hash,
    optional_text,
    read_fda_excel,
    require_columns,
    required_date,
    required_identifier,
    required_text,
    row_value,
)
from qualifyze.typing import ComplianceAction


class ComplianceActionLoader:
    def __init__(self) -> None:
        self._required_columns = {
            "fei_number": ("FEI Number",),
            "legal_name": ("Legal Name",),
            "state": ("State",),
            "country_area": ("Country/Area",),
            "product_type": ("Product Type",),
            "action_taken_date": (
                "Action Taken Date",
            ),
            "action_type": ("Action Type",),
            "case_injunction_id": (
                "Case/Injunction ID",
            ),
        }

    def load(
        self,
        path: Path,
    ) -> list[ComplianceAction]:
        frame = read_fda_excel(path)

        require_columns(
            frame,
            self._required_columns,
            filename=path.name,
        )

        actions: list[ComplianceAction] = []

        for excel_row, (_, row) in enumerate(
            frame.iterrows(),
            start=2,
        ):
            try:
                values = {
                    "fei_number": required_identifier(
                        row_value(row, "FEI Number"),
                        field="FEI Number",
                    ),
                    "legal_name": required_text(
                        row_value(row, "Legal Name"),
                        field="Legal Name",
                    ),
                    "state": optional_text(
                        row_value(row, "State"),
                        null_values={"-"},
                    ),
                    "country_area": required_text(
                        row_value(row, "Country/Area"),
                        field="Country/Area",
                    ),
                    "product_type": required_text(
                        row_value(row, "Product Type"),
                        field="Product Type",
                    ),
                    "action_taken_date": required_date(
                        row_value(
                            row,
                            "Action Taken Date",
                        ),
                        field="Action Taken Date",
                    ),
                    "action_type": required_text(
                        row_value(row, "Action Type"),
                        field="Action Type",
                    ),
                    "case_injunction_id": (
                        required_identifier(
                            row_value(
                                row,
                                "Case/Injunction ID",
                            ),
                            field="Case/Injunction ID",
                        )
                    ),
                }

                values["hash"] = calculate_hash(values)

                actions.append(
                    ComplianceAction(**values)
                )
            except (TypeError, ValueError) as exc:
                raise FdaExcelError(
                    f"{path.name}, row {excel_row}: {exc}"
                ) from exc

        return actions