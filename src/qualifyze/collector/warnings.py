import datetime
import hashlib
import json
import logging
import time
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import replace
from types import TracebackType
from typing import Any, Self
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from qualifyze.config import WarningLettersRetrieverConfig
from qualifyze.typing import WarningLetter

logger = logging.getLogger(__name__)


class WarningLetterParsingError(Exception):
    pass

class InvalidFDAUrlError(ValueError):
    pass


class WarningLettersRetriever:
    def __init__(self, config: WarningLettersRetrieverConfig) -> None:
        self._config = config
        self._last_request_started_at: float | None = None
        self._datatable_settings: (
            tuple[str, dict[str, str]] | None
        ) = None
        self._draw = 0
        
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

        content = "\n".join(main_element.stripped_strings)
        warning_letter_summary = "\n".join([
            str(letter.posted_date),
            str(letter.company_name),
            str(letter.url),
            str(content),
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
        *,
        params: dict | None = None,
        headers: Mapping[str, str] | None = None,
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
        html = self._fetch_html(url)
        logger.info("Fetched warning-letter detail: %s", url)
        return html

    def _get_datatable_settings(
        self,
    ) -> tuple[str, dict[str, str]]:
        if self._datatable_settings is not None:
            endpoint, base_params = self._datatable_settings
            return endpoint, base_params.copy()

        html = self._fetch_html(str(self._config.url))
        soup = BeautifulSoup(html, "html.parser")

        settings_element = soup.select_one(
            'script[data-drupal-selector="drupal-settings-json"]'
        )

        if not isinstance(settings_element, Tag):
            raise WarningLetterParsingError(
                "Could not find FDA Drupal settings"
            )

        raw_settings = settings_element.string

        if raw_settings is None:
            raise WarningLetterParsingError(
                "FDA Drupal settings are empty"
            )

        try:
            settings: dict[str, Any] = json.loads(raw_settings)
        except json.JSONDecodeError as error:
            raise WarningLetterParsingError(
                "Could not decode FDA Drupal settings"
            ) from error

        datatables = settings.get("datatables")

        if not isinstance(datatables, dict) or not datatables:
            raise WarningLetterParsingError(
                "Could not find FDA DataTables configuration"
            )

        table_settings = next(iter(datatables.values()))

        if not isinstance(table_settings, dict):
            raise WarningLetterParsingError(
                "Unexpected FDA DataTables configuration"
            )

        ajax_settings = table_settings.get("ajax")

        if not isinstance(ajax_settings, dict):
            raise WarningLetterParsingError(
                "Could not find FDA DataTables AJAX configuration"
            )

        ajax_path = ajax_settings.get("url")
        ajax_data = ajax_settings.get("data")

        if not isinstance(ajax_path, str):
            raise WarningLetterParsingError(
                "Could not find FDA DataTables endpoint"
            )

        if not isinstance(ajax_data, dict):
            raise WarningLetterParsingError(
                "Could not find FDA DataTables base parameters"
            )

        endpoint = urljoin(
            self._config.fda_url,
            ajax_path,
        )

        base_params = {
            str(key): "" if value is None else str(value)
            for key, value in ajax_data.items()
        }

        self._datatable_settings = endpoint, base_params
        return endpoint, base_params.copy()

    def _build_datatable_params(
        self,
        base_params: dict[str, str],
        *,
        start: int,
        length: int,
    ) -> dict[str, str | int]:
        self._draw += 1

        params: dict[str, str | int] = {
            **base_params,
            "search_api_fulltext": "",
            "search_api_fulltext_issuing_office": "",
            "field_letter_issue_datetime": "All",
            "field_change_date_closeout_letter": "",
            "field_change_date_response_letter": "",
            "field_change_date_2": "All",
            "field_letter_issue_datetime_2": "",
            "draw": self._draw,
            "start": start,
            "length": length,
            "search[value]": "",
            "search[regex]": "false",
        }

        for column_index in range(8):
            prefix = f"columns[{column_index}]"

            params[f"{prefix}[data]"] = column_index
            params[f"{prefix}[name]"] = ""
            params[f"{prefix}[searchable]"] = "true"
            params[f"{prefix}[orderable]"] = (
                "false" if column_index == 7 else "true"
            )
            params[f"{prefix}[search][value]"] = ""
            params[f"{prefix}[search][regex]"] = "false"

        return params

    def _fetch_warning_letter_batch(
        self,
        *,
        start: int,
        length: int,
    ) -> dict[str, Any]:
        endpoint, base_params = self._get_datatable_settings()

        params = self._build_datatable_params(
            base_params,
            start=start,
            length=length,
        )

        response = self._get(
            endpoint,
            params=params,
            headers={
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        try:
            payload = response.json()
        except ValueError as error:
            raise WarningLetterParsingError(
                "FDA DataTables response was not valid JSON"
            ) from error

        if not isinstance(payload, dict):
            raise WarningLetterParsingError(
                "Unexpected FDA DataTables response structure"
            )

        return payload

    def _parse_datatable_rows(
        self,
        payload: dict[str, Any],
    ) -> list[WarningLetter]:
        rows = payload.get("data")

        if not isinstance(rows, list):
            raise WarningLetterParsingError(
                "FDA DataTables response does not contain data"
            )

        letters: list[WarningLetter] = []

        for row_index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) < 5:
                logger.warning(
                    "Skipping malformed DataTables row %d",
                    row_index,
                )
                continue

            company_url = self._get_fragment_url(row[2])

            if company_url is None:
                logger.warning(
                    "Skipping row %d without company URL",
                    row_index,
                )
                continue

            letters.append(
                WarningLetter(
                    posted_date=self._parse_date(
                        self._get_fragment_text(row[0])
                    ),
                    issue_date=self._parse_date(
                        self._get_fragment_text(row[1])
                    ),
                    company_name=self._get_fragment_text(row[2]),
                    url=company_url,
                    issuing_office=self._get_fragment_text(row[3]),
                    subject=self._get_fragment_text(row[4]),
                )
            )

        return letters

    def retrieve(
        self,
        start: int = 0,
        length: int = 10,
    ) -> list[WarningLetter]:
        if start < 0:
            raise ValueError("start must be zero or greater")

        if length <= 0:
            raise ValueError("length must be greater than zero")

        payload = self._fetch_warning_letter_batch(
            start=start,
            length=length,
        )

        letters = self._parse_datatable_rows(payload)

        logger.info(
            "Parsed %d warning letters start=%d length=%d total=%s",
            len(letters),
            start,
            length,
            payload.get("recordsTotal"),
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
    def _get_fragment_text(fragment: object) -> str:
        soup = BeautifulSoup(str(fragment), "html.parser")
        return " ".join(soup.stripped_strings)


    def _get_fragment_url(
        self,
        fragment: object,
    ) -> str | None:
        soup = BeautifulSoup(str(fragment), "html.parser")
        link = soup.find("a", href=True)

        if not isinstance(link, Tag):
            return None

        href = link.get("href")

        if not isinstance(href, str):
            return None

        return urljoin(self._config.fda_url, href)

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
