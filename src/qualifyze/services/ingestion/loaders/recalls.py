from pathlib import Path

from qualifyze.services.ingestion.loaders._excel import (
    FdaExcelError,
    calculate_hash,
    optional_date,
    optional_text,
    read_fda_excel,
    require_columns,
    required_identifier,
    required_text,
    row_value,
)
from qualifyze.typing import Recall


class RecallsLoader:
    def __init__(self) -> None:
        self._required_columns = {
            "fei_number": ("FEI Number",),
            "legal_name": ("Recalling Firm Name",),
            "product_type": ("Product Type",),
            "product_classification": ("Product Classification",),
            "status": ("Status",),
            "distribution_partner": ("Distribution Pattern",),
            "recalling_firm_city": ("Recalling Firm City",),
            "recalling_firm_state": ("Recalling Firm State",),
            "recalling_firm_country": ("Recalling Firm Country",),
            "center_classification_date": ("Center Classification Date",),
            "reason_recall": ("Reason for Recall",),
            "product_description": ("Product Description",),
            "event_id": ("Event ID",),
            "event_classification": ("Event Classification",),
            "product_id": ("Product ID",),
            "center": ("Center",),
            "recall_details": ("Recall Details",),
        }

    def load(
        self,
        path: Path,
    ) -> list[Recall]:
        frame = read_fda_excel(path)

        require_columns(
            frame,
            self._required_columns,
            filename=path.name,
        )

        inspections: list[Recall] = []

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
                        row_value(row, "Recalling Firm Name"),
                        field="Recalling Firm Name",
                    ),
                    "product_type": optional_text(
                        row_value(row, "Product Type")
                    ),
                    "product_classification": optional_text(
                        row_value(row, "Product Classification")
                    ),
                    "status": required_text(
                        row_value(row, "Status"),
                        field="Status",
                    ),
                    "distribution_partner": optional_text(
                        row_value(row, "Distribution Pattern")
                    ),
                    "recalling_firm_city": optional_text(
                        row_value(row, "Recalling Firm City")
                    ),
                    "recalling_firm_state": optional_text(
                        row_value(row, "Recalling Firm State")
                    ),
                    "recalling_firm_country": optional_text(
                        row_value(row, "Recalling Firm Country")
                    ),
                    "center_classification_date": optional_date(
                        row_value(row, "Center Classification Date"),
                        field="Center Classification Date",
                    ),
                    "reason_recall": optional_text(
                        row_value(row, "Reason for Recall")
                    ),
                    "product_description": optional_text(
                        row_value(row, "Product Description")
                    ),
                    "event_id": required_text(
                        row_value(row, "Event ID"),
                        field="Event ID"
                    ),
                    "event_classification": optional_text(
                        row_value(row, "Event Classification")
                    ),
                    "product_id": optional_text(
                        row_value(row, "Product ID")
                    ),
                    "center": optional_text(
                        row_value(row, "Center")
                    ),
                    "recall_details": optional_text(
                        row_value(row, "Recall Details")
                    ),
                }

                values["hash"] = calculate_hash(values)

                inspections.append(
                    Recall(**values)
                )
            except (TypeError, ValueError) as exc:
                raise FdaExcelError(
                    f"{path.name}, row {excel_row}: {exc}"
                ) from exc

        return inspections