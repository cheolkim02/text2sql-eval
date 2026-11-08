"""Small helpers that turn ``json.loads`` output into precisely typed values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from text2sql_eval.errors import InputError


def read_utf8(path: Path) -> str:
    """Read a whole text file as UTF-8, turning OS and decoding errors into InputError.

    A leading byte order mark is dropped: Windows editors and Excel add one, and
    left in place it would break the first JSON line or prefix the first SQL.
    """
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise InputError(path, "file not found", hint="check the path") from None
    except UnicodeDecodeError as exc:
        raise InputError(
            path,
            f"not valid UTF-8 (byte {exc.start})",
            hint="save the file with UTF-8 encoding",
        ) from None


def parse_json(text: str, path: Path, location: str | None = None) -> object:
    """Parse JSON text, reporting syntax errors with their position."""
    try:
        value: object = json.loads(text)
    except json.JSONDecodeError as exc:
        where = location or f"line {exc.lineno}"
        raise InputError(
            path,
            f"invalid JSON at column {exc.colno}: {exc.msg}",
            location=where,
            hint="check quotes, commas and brackets on this line",
        ) from None
    return value


def as_object(value: object) -> dict[str, object] | None:
    """Return ``value`` as a JSON object, or ``None`` if it is something else."""
    if not isinstance(value, dict):
        return None
    # JSON object keys are always strings, so this narrowing is exact.
    return cast("dict[str, object]", value)


def as_array(value: object) -> list[object] | None:
    """Return ``value`` as a JSON array, or ``None`` if it is something else."""
    if not isinstance(value, list):
        return None
    # Elements are arbitrary JSON values, which ``object`` describes exactly.
    return cast("list[object]", value)


def json_type_name(value: object) -> str:
    """Name a JSON value's type the way users see it in the file."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"
