import datetime
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import pandas as pd
from pandas import DataFrame, Series
from pandas.api.types import is_scalar


class FdaExcelError(ValueError):
    """Raised when an FDA Excel file cannot be parsed."""


def read_fda_excel(path: Path) -> DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"FDA Excel file does not exist: {path}"
        )

    try:
        frame = pd.read_excel(
            path,
            dtype=object,
            engine="openpyxl",
        )
    except Exception as exc:
        raise FdaExcelError(
            f"Could not read FDA Excel file: {path}"
        ) from exc

    # Remove accidental whitespace from Excel headers.
    frame.columns = [
        str(column).strip()
        for column in frame.columns
    ]

    # Completely empty Excel rows should not become records.
    return frame.dropna(how="all")


def require_columns(
    frame: DataFrame,
    required: Mapping[str, Sequence[str]],
    *,
    filename: str,
) -> None:
    """
    Validate logical columns.

    Each logical column can have several accepted FDA header names.
    """
    available = set(frame.columns)
    missing: list[str] = []

    for logical_name, alternatives in required.items():
        if not any(
            column in available
            for column in alternatives
        ):
            accepted = " or ".join(alternatives)
            missing.append(
                f"{logical_name} ({accepted})"
            )

    if missing:
        raise FdaExcelError(
            f"{filename} is missing required columns: "
            f"{', '.join(missing)}"
        )


def row_value(
    row: Series,
    *column_names: str,
) -> object:
    for column_name in column_names:
        if column_name in row.index:
            return row[column_name]

    return None


def is_missing(value: object) -> bool:
    if value is None:
        return True

    # Protect against accidentally passing a list, Series,
    # array or another non-scalar object.
    if not is_scalar(value):
        return False

    result = pd.isna(cast(Any, value))

    return bool(result)


def optional_text(
    value: object,
    *,
    null_values: set[str] | None = None,
) -> str | None:
    if is_missing(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    if null_values and text.casefold() in {
        item.casefold()
        for item in null_values
    }:
        return None

    return text


def required_text(
    value: object,
    *,
    field: str,
) -> str:
    text = optional_text(value)

    if text is None:
        raise FdaExcelError(
            f"{field} is required"
        )

    return text


def optional_identifier(
    value: object,
) -> str | None:
    """
    Convert Excel identifiers into strings.

    For example:
        3012457996.0 -> "3012457996"

    Identifiers remain strings because they are labels, not quantities.
    """
    if is_missing(value):
        return None

    if isinstance(value, bool):
        raise FdaExcelError(
            f"Boolean value is not a valid identifier: {value}"
        )

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

        if value.is_integer():
            return str(int(value))

    text = str(value).strip()

    if not text:
        return None

    # Handle values pandas may represent as "12345.0".
    integer_part, separator, decimal_part = text.partition(".")

    if (
        separator
        and integer_part.isdigit()
        and decimal_part
        and set(decimal_part) == {"0"}
    ):
        return integer_part

    return text


def required_identifier(
    value: object,
    *,
    field: str,
) -> str:
    identifier = optional_identifier(value)

    if identifier is None:
        raise FdaExcelError(
            f"{field} is required"
        )

    return identifier


def required_integer(
    value: object,
    *,
    field: str,
) -> int:
    identifier = required_identifier(
        value,
        field=field,
    )

    try:
        return int(identifier)
    except ValueError as exc:
        raise FdaExcelError(
            f"{field} must be an integer; "
            f"received {value!r}"
        ) from exc


def optional_integer(
    value: object,
    *,
    field: str,
) -> int | None:
    identifier = optional_identifier(value)

    if identifier is None:
        return None

    try:
        return int(identifier)
    except ValueError as exc:
        raise FdaExcelError(
            f"{field} must be an integer; "
            f"received {value!r}"
        ) from exc


def optional_date(
    value: object,
    *,
    field: str,
) -> datetime.date | None:
    if is_missing(value):
        return None

    if isinstance(value, datetime.datetime):
        return value.date()

    if isinstance(value, datetime.date):
        return value

    if isinstance(value, str):
        text = value.strip()

        if not text or text.casefold() in {
            "-",
            "n/a",
            "na",
            "none",
            "null",
        }:
            return None

        parsed = pd.to_datetime(
            text,
            errors="coerce",
        )

        if not isinstance(parsed, pd.Timestamp):
            raise FdaExcelError(
                f"{field} contains an invalid date: {value!r}"
            )

        return parsed.date()

    raise FdaExcelError(
        f"{field} contains an unsupported date value: "
        f"{value!r} ({type(value).__name__})"
    )


def required_date(
    value: object,
    *,
    field: str,
) -> datetime.date:
    parsed = optional_date(
        value,
        field=field,
    )

    if parsed is None:
        raise FdaExcelError(
            f"{field} is required"
        )

    return parsed


def optional_boolean(
    value: object,
    *,
    field: str,
) -> bool | None:
    if is_missing(value):
        return None

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().casefold()

    true_values = {
        "yes",
        "y",
        "true",
        "1",
        "posted",
    }
    false_values = {
        "no",
        "n",
        "false",
        "0",
        "not posted",
    }

    if normalized in true_values:
        return True

    if normalized in false_values:
        return False

    raise FdaExcelError(
        f"{field} contains an invalid boolean: {value!r}"
    )


def classification_code(
    classification: str | None,
    explicit_code: object = None,
) -> str | None:
    explicit = optional_text(explicit_code)

    if explicit:
        code = explicit.upper()

        if code not in {"NAI", "VAI", "OAI"}:
            raise FdaExcelError(
                "Classification Code must be "
                "NAI, VAI or OAI"
            )

        return code

    if classification is None:
        return None

    normalized = classification.upper()

    for code in ("NAI", "VAI", "OAI"):
        if normalized == code or f"({code})" in normalized:
            return code

    return None


def calculate_hash(
    values: Mapping[str, Any],
) -> str:
    normalized = {
        key: _json_value(value)
        for key, value in values.items()
    }

    payload = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(
        value,
        (datetime.date, datetime.datetime),
    ):
        return value.isoformat()

    return value