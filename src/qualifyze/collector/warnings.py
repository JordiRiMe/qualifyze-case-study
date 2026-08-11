from dataclasses import replace
import datetime
import hashlib
import logging
import time
from collections.abc import Iterable, Iterator
from types import TracebackType
from typing import Self
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from qualifyze.config import WarningLettersRetrieverConfig
from qualifyze.typing import EXPECTED_HEADERS, WarningLetter

logger = logging.getLogger(__name__)


class WarningLetterParsingError(Exception):
    pass

class InvalidFDAUrlError(ValueError):
    pass


class WarningLettersRetriever:
    def __init__(self, config: WarningLettersRetrieverConfig) -> None:
        self._config = config
        self._last_request_started_at: float | None = None
        self._client = httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers={**self._config.headers},
        )

    def _validate_fda_url(self, url: str) -> None:
        parsed = urlparse(url)
        expected_fda_parsed = urlparse(self._config.fda_url)

        if parsed.scheme != "https" or parsed.hostname != expected_fda_parsed.hostname:
            raise InvalidFDAUrlError(
                f"Refusing to retrieve non-FDA URL: {url}"
            )

    def _fetch_warning_letter_page(self, page: int=0) -> str:
        """
        Get HTML content from a specific page of the table
        """
        response = self._client.get(
            url=self._config.url,
            params={"page": page},
        )
        response.raise_for_status()
        logger.info(
            "Fetched page=%d status=%d",
            page,
            response.status_code,
        )
        return response.text

    def _find_warning_letters_table(self, soup: BeautifulSoup) -> Tag:
        """
        Soup to find warning letters table in a specific page
        """
        for table in soup.find_all("table"):
            headers = {
                self._get_text(header)
                for header in table.select("thead th")
            }

            if EXPECTED_HEADERS.issubset(headers):
                return table

        raise WarningLetterParsingError(
            "Could not find the FDA warning-letter table"
        )

    def _parse_warning_letters(self, html: str) -> list[WarningLetter]:
        """
        Parse the table information of each Warning LEtter from the FDA table
        """
        soup = BeautifulSoup(html, "html.parser")
        table = self._find_warning_letters_table(soup)

        headers = [
            self._get_text(header)
            for header in table.select("thead th")
        ]

        letters: list[WarningLetter] = []

        for row in table.select("tbody tr"):
            cells = row.find_all("td", recursive=False)

            if len(cells) != len(headers):
                continue

            values = dict(zip(headers, cells, strict=True))
            company_url = self._get_url(values["Company Name"])

            if company_url is None:
                continue

            letters.append(
                WarningLetter(
                    posted_date=self._parse_date(
                        self._get_text(values["Posted Date"])
                    ),
                    issue_date=self._parse_date(
                        self._get_text(values["Letter Issue Date"])
                    ),
                    company_name=self._get_text(values["Company Name"]),
                    url=company_url,
                    issuing_office=self._get_text(values["Issuing Office"]),
                    subject=self._get_text(values["Subject"]),
                )
            )

        return letters

    def _parse_warning_letter_detail(
        self,
        letter: WarningLetter,
        html: str,
    ) -> WarningLetter:
        soup = BeautifulSoup(html, "html.parser")

        title_element = soup.select_one("main h1")
        main_element = soup.select_one("main")

        if title_element is None:
            raise WarningLetterParsingError(
                f"Could not find warning-letter title: {letter.url}"
            )

        if main_element is None:
            raise WarningLetterParsingError(
                f"Could not find warning-letter content: {letter.url}"
            )

        title = self._get_text(title_element)
        content = "\n".join(main_element.stripped_strings)
        warning_letter_summary = "\n".join([
            str(letter.posted_date),
            str(letter.company_name),
            str(letter.url),
            str(letter.content),
        ])
        warning_letter_hash = hashlib.sha256(warning_letter_summary.encode('utf-8')).hexdigest()

        return replace(
            letter,
            title=self._get_text(title_element),
            content=content,
            hash=warning_letter_hash,
        )

    def _wait_for_crawl_delay(self) -> None:
        if self._last_request_started_at is None:
            return

        elapsed = time.monotonic() - self._last_request_started_at
        remaining = 30.0 - elapsed

        if remaining > 0:
            logger.info(
                "Waiting %.1f seconds before next FDA request",
                remaining,
            )
            time.sleep(remaining)

    def _get(
        self,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        """Method to get the URL content from a specific warning letter"""
        self._validate_fda_url(url)
        self._wait_for_crawl_delay()

        self._last_request_started_at = time.monotonic()

        response = self._client.get(
            url,
            params=params,
            headers=headers,
        )
        response.raise_for_status()

        return response

    def _fetch_html(
        self,
        url: str,
        *,
        params: dict[str, object] | None = None,
    ) -> str:
        response = self._get(url, params=params)
        content_type = response.headers.get("content-type", "")

        if "text/html" not in content_type:
            raise WarningLetterParsingError(
                f"Expected HTML from {url}, received {content_type!r}"
            )

        return response.text

    def _fetch_warning_letter_detail(self, url: str) -> str:
        """
        Get specific content from the URL of a warning letter (text of the URL/html)
        """
        response = self._get(
            url=url,
            headers={**self._config.headers},
        )
        content_type = response.headers.get("content-type", "")

        if "text/html" not in content_type:
            raise WarningLetterParsingError(
                f"Expected HTML from {url}, received {content_type!r}"
            )

        logger.info("Fetched warning-letter detail: %s", url)
        return response.text

    def retrieve(self, page: int=0) -> list[WarningLetter]:
        html = self._fetch_html(
            str(self._config.url),
            params={"page": page},
        )
        letters = self._parse_warning_letters(html)

        logger.info(
            "Parsed %d warning letters from page %d",
            len(letters),
            page,
        )

        return letters

    def retrieve_detail(
        self,
        letter: WarningLetter,
    ) -> WarningLetter:
        html = self._fetch_warning_letter_detail(letter.url)

        return self._parse_warning_letter_detail(
            letter=letter,
            html=html,
        )

    def retrieve_details(
        self,
        letters: Iterable[WarningLetter],
    ) -> Iterator[WarningLetter]:
        for index, letter in enumerate(letters, start=1):
            logger.info(
                "Retrieving detail %d: %s",
                index,
                letter.url,
            )

            yield self.retrieve_detail(letter)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @staticmethod
    def _parse_date(value: str) -> datetime.date:
        parsed = datetime.datetime.strptime(  # noqa: DTZ007
            value.strip(),
            "%m/%d/%Y",
        )
        return parsed.date()

    @staticmethod
    def _get_text(cell: Tag) -> str:
        return " ".join(cell.stripped_strings)

    def _get_url(self, cell: Tag) -> str | None:
        link = cell.find("a", href=True)

        if not isinstance(link, Tag):
            return None

        href = link.get("href")

        if not isinstance(href, str):
            return None

        return urljoin(self._config.fda_url, href)
