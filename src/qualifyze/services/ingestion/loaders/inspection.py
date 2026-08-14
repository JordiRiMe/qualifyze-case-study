from pathlib import Path

from qualifyze.services.ingestion.loaders._excel import (
    FdaExcelError,
    calculate_hash,
    classification_code,
    optional_boolean,
    optional_date,
    optional_identifier,
    optional_integer,
    optional_text,
    read_fda_excel,
    require_columns,
    required_date,
    required_integer,
    required_text,
    row_value,
)
from qualifyze.typing import Inspection


class InspectionLoader:
    def __init__(self) -> None:
        self._required_columns = {
            "inspection_id": ("Inspection ID",),
            "fei_number": ("FEI Number",),
            "legal_name": ("Legal Name",),
            "city": ("City",),
            "state": ("State",),
            "zip_code": (
                "Zip Code",
                "ZIP Code",
                "Zip",
            ),
            "country": (
                "Country/Area",
                "Country",
            ),
            "inspection_end_date": (
                "Inspection End Date",
            ),
            "fiscal_year": ("Fiscal Year",),
            "posted_citations": (
                "Posted Citations",
            ),
            "classification": ("Classification",),
            "project_area": ("Project Area",),
            "product_type": ("Product Type",),
            "additional_details": (
                "Additional Details",
            ),
            "fmd_145_date": (
                "FMD-145 Date",
                "FMD 145 Date",
            ),
        }

    def load(
        self,
        path: Path,
    ) -> list[Inspection]:
        frame = read_fda_excel(path)

        require_columns(
            frame,
            self._required_columns,
            filename=path.name,
        )

        inspections: list[Inspection] = []

        for excel_row, (_, row) in enumerate(
            frame.iterrows(),
            start=2,
        ):
            try:
                classification = optional_text(
                    row_value(row, "Classification")
                )

                values = {
                    "inspection_id": required_integer(
                        row_value(row, "Inspection ID"),
                        field="Inspection ID",
                    ),
                    "fei_number": optional_identifier(
                        row_value(row, "FEI Number")
                    ),
                    "legal_name": optional_text(
                        row_value(row, "Legal Name")
                    ),
                    "city": optional_text(
                        row_value(row, "City")
                    ),
                    "state": optional_text(
                        row_value(row, "State"),
                        null_values={"-"},
                    ),
                    "zip_code": optional_identifier(
                        row_value(
                            row,
                            "Zip Code",
                            "ZIP Code",
                            "Zip",
                        )
                    ),
                    "country": optional_text(
                        row_value(
                            row,
                            "Country/Area",
                            "Country",
                        )
                    ),
                    "inspection_end_date": required_date(
                        row_value(
                            row,
                            "Inspection End Date",
                        ),
                        field="Inspection End Date",
                    ),
                    "fiscal_year": optional_integer(
                        row_value(row, "Fiscal Year"),
                        field="Fiscal Year",
                    ),
                    "posted_citations": optional_boolean(
                        row_value(
                            row,
                            "Posted Citations",
                        ),
                        field="Posted Citations",
                    ),
                    "classification": classification,
                    "classification_code": (
                        classification_code(
                            classification,
                            row_value(
                                row,
                                "Classification Code",
                            ),
                        )
                    ),
                    "project_area": required_text(
                        row_value(row, "Project Area"),
                        field="Project Area",
                    ),
                    "product_type": optional_text(
                        row_value(row, "Product Type")
                    ),
                    "additional_details": optional_text(
                        row_value(
                            row,
                            "Additional Details",
                        )
                    ),
                    "fmd_145_date": optional_date(
                        row_value(
                            row,
                            "FMD-145 Date",
                            "FMD 145 Date",
                        ),
                        field="FMD-145 Date",
                    ),
                }

                values["hash"] = calculate_hash(values)

                inspections.append(
                    Inspection(**values)
                )
            except (TypeError, ValueError) as exc:
                raise FdaExcelError(
                    f"{path.name}, row {excel_row}: {exc}"
                ) from exc

        return inspections