from dataclasses import dataclass
from datetime import date

EXPECTED_HEADERS = {
    "Posted Date",
    "Letter Issue Date",
    "Company Name",
    "Issuing Office",
    "Subject",
}


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
    