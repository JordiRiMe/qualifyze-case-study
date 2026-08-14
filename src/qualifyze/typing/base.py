from dataclasses import dataclass
from datetime import date
from enum import Enum

type WarningLetterIdentity = tuple[date, str]


@dataclass(frozen=True, slots=True)
class WarningLetter:
    posted_date: date
    issue_date: date
    company_name: str
    url: str
    issuing_office: str
    subject: str
    title: str | None = None
    content: str | None = None
    hash: str | None = None

    @property
    def has_detail(self) -> bool:
        return self.title is not None and self.content is not None

    @property
    def identity(self) -> WarningLetterIdentity:
        return (
            self.posted_date,
            self.url,
        )


@dataclass(frozen=True, slots=True)
class IngestionResult:
    batches: int
    discovered: int
    stored: int
    failed: int


class FEIClassification(Enum):
    NAI = "No action indicated"
    VAI = "Voluntary action indicated"
    OAI = "Official action indicated"


class ProductType(Enum):
    BIOLOGICS = "Biologics"
    DEVICES = "Devices"
    DRUGS = "Drugs"
    FOODCOSMETICS = "Food/Cosmetics"
    TOBACCO = "Tobacco"
    VETERINARY = "Veterinary"

class ActionType(Enum):
    INJUNCTION = "Injunction"
    SEIZURE = "Seizure"
    WARNINGLETTER = "Warning Letter"
