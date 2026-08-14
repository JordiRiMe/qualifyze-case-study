import datetime
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Inspection:
    inspection_id: int
    fei_number: str | None
    legal_name: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    country: str | None
    inspection_end_date: datetime.date
    fiscal_year: int | None
    posted_citations: bool | None
    classification: str | None
    classification_code: str | None
    project_area: str
    product_type: str | None
    additional_details: str | None
    fmd_145_date: datetime.date | None
    hash: str | None


@dataclass(frozen=True, slots=True)
class InspectionCitation:
    inspection_id: int
    fei_number: str | None
    legal_name: str
    inspection_end_date: datetime.date
    program_area: str
    act_cfr_number: str
    short_description: str | None
    long_description: str | None
    hash: str | None


@dataclass(frozen=True, slots=True)
class ComplianceAction:
    fei_number: str
    legal_name: str
    state: str | None
    country_area: str
    product_type: str
    action_taken_date: datetime.date
    action_type: str
    case_injunction_id: str
    hash: str


@dataclass(frozen=True, slots=True)
class Recall:
    fei_number: str
    legal_name: str
    product_type: str
    product_classification: str
    status: str
    distribution_partner: str
    recalling_firm_city: str
    recalling_firm_state: str
    recalling_firm_country: str
    center_classification_date: str
    reason_recall: str
    product_description: str
    event_id: str
    event_classification: str
    product_id: str
    center: str
    recall_details: str
    hash: str
