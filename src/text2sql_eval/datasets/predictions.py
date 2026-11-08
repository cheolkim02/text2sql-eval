"""Load model predictions in the two formats from ADR 0018.

* Text: one single-line SQL per line; line N predicts the dataset's N-th case.
* JSONL: one JSON object per line with ``id``, ``sql`` and optional ``meta``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from text2sql_eval.datasets._json import (
    as_object,
    json_type_name,
    parse_json,
    read_utf8,
)
from text2sql_eval.datasets.bird import Dataset
from text2sql_eval.errors import InputError

# How many missing ids to list in an error before summarising the rest.
_MAX_IDS_SHOWN = 5


@dataclass(frozen=True)
class Prediction:
    """A model's SQL for one case. An empty ``sql`` means the model gave none."""

    case_id: str
    sql: str
    meta: dict[str, object] = field(default_factory=dict[str, object])


def load_text_predictions(path: Path, dataset: Dataset) -> dict[str, Prediction]:
    """Read a text file with one SQL per line, matched to cases by position.

    Lines are split on ``\\n`` only (a trailing ``\\r`` is dropped), so Unicode
    line separators inside a SQL string do not shift later lines. Surrounding
    whitespace is removed. An empty line is an empty prediction, which keeps
    every later line aligned with its case. A single newline at the end of the
    file is allowed.

    Raises:
        InputError: if the file is unreadable or its line count differs from
            the number of cases.

    Example:
        >>> preds = load_text_predictions(Path("preds.txt"), dataset)
        >>> preds[dataset.cases[0].id].sql
        'SELECT ...'
    """
    lines = read_utf8(path).split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    expected = len(dataset.cases)
    if len(lines) != expected:
        raise InputError(
            path,
            f"has {len(lines)} lines but the dataset {dataset.path} has {expected} cases",
            hint=(
                "write exactly one line per case, in dataset order; "
                "keep an empty line where the model produced no SQL"
            ),
        )
    return {
        case.id: Prediction(case_id=case.id, sql=line.strip())
        for case, line in zip(dataset.cases, lines, strict=True)
    }


def load_jsonl_predictions(
    path: Path, dataset: Dataset, *, allow_missing: bool = False
) -> dict[str, Prediction]:
    """Read a JSONL file where each line is ``{"id": ..., "sql": ..., "meta": {...}}``.

    ``id`` may be an integer or a string and is matched against case ids as a
    string (``718`` and ``"718"`` are the same case). Blank lines are skipped.

    Args:
        path: The JSONL file.
        dataset: The cases the predictions belong to.
        allow_missing: If true, cases without a line are left out of the
            result instead of raising an error.

    Raises:
        InputError: on invalid JSON, a non-object line, a missing or mistyped
            field, an id not in the dataset, a repeated id, or (unless
            ``allow_missing``) cases with no prediction.

    Example:
        >>> preds = load_jsonl_predictions(Path("preds.jsonl"), dataset)
        >>> preds["718"].meta
        {'latency_ms': 1830}
    """
    known = set(dataset.ids)
    predictions: dict[str, Prediction] = {}
    first_line: dict[str, int] = {}
    for line_number, line in enumerate(read_utf8(path).split("\n"), start=1):
        if not line.strip():
            continue
        location = f"line {line_number}"
        prediction = _parse_prediction_line(line, path, location)
        case_id = prediction.case_id
        if case_id not in known:
            raise InputError(
                path,
                f"id {case_id} is not in the dataset {dataset.path}",
                location=location,
                hint="ids must match the dataset's question ids",
            )
        if case_id in first_line:
            raise InputError(
                path,
                f"id {case_id} appears twice (first on line {first_line[case_id]})",
                location=location,
                hint="keep one prediction per case",
            )
        first_line[case_id] = line_number
        predictions[case_id] = prediction

    missing = [case_id for case_id in dataset.ids if case_id not in predictions]
    if missing and not allow_missing:
        shown = ", ".join(missing[:_MAX_IDS_SHOWN])
        more = len(missing) - _MAX_IDS_SHOWN
        listing = shown if more <= 0 else f"{shown} and {more} more"
        raise InputError(
            path,
            f"{len(missing)} of {len(dataset.cases)} cases have no prediction: {listing}",
            hint="add a line for each case, or allow missing predictions",
        )
    return predictions


def _parse_prediction_line(line: str, path: Path, location: str) -> Prediction:
    value = parse_json(line, path, location)
    obj = as_object(value)
    if obj is None:
        raise InputError(
            path,
            f"expected a JSON object, found {json_type_name(value)}",
            location=location,
            hint='each line should look like {"id": 718, "sql": "SELECT ..."}',
        )

    for key in ("id", "sql"):
        if key not in obj:
            raise InputError(
                path,
                f"missing field '{key}'",
                location=location,
                hint='each line should look like {"id": 718, "sql": "SELECT ..."}',
            )

    raw_id = obj["id"]
    if isinstance(raw_id, bool) or not isinstance(raw_id, int | str) or raw_id == "":
        raise InputError(
            path,
            "'id' must be an integer or a non-empty string, "
            f"found {json_type_name(raw_id)}",
            location=location,
        )

    sql = obj["sql"]
    if not isinstance(sql, str):
        raise InputError(
            path,
            f"'sql' must be a string, found {json_type_name(sql)}",
            location=location,
            hint='use "" when the model produced no SQL',
        )

    meta_value = obj.get("meta", {})
    meta = as_object(meta_value)
    if meta is None:
        raise InputError(
            path,
            f"'meta' must be an object, found {json_type_name(meta_value)}",
            location=location,
        )
    return Prediction(case_id=str(raw_id), sql=sql.strip(), meta=meta)
