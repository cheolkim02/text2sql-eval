"""Load evaluation cases from a BIRD-format question file (for example ``dev.json``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from text2sql_eval.datasets._json import (
    as_array,
    as_object,
    json_type_name,
    parse_json,
    read_utf8,
)
from text2sql_eval.errors import InputError

# A constrained TypeVar instead of 3.12's ``def f[T: (int, str)]`` (ADR 0009).
_Scalar = TypeVar("_Scalar", int, str)


@dataclass(frozen=True)
class Case:
    """One evaluation question with its gold SQL.

    ``id`` is the dataset's question id as a string (BIRD's integer
    ``question_id`` 718 becomes ``"718"``), so ids from any source compare the
    same way.
    """

    id: str
    db_id: str
    question: str
    evidence: str
    gold_sql: str
    difficulty: str | None


@dataclass(frozen=True)
class Dataset:
    """Cases in file order. Order matters: text prediction files follow it."""

    path: Path
    cases: tuple[Case, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        """Case ids in file order."""
        return tuple(case.id for case in self.cases)


def load_bird(path: Path) -> Dataset:
    """Read a BIRD question file: a JSON array of question objects.

    Each object needs ``question_id`` (integer), ``db_id``, ``question``,
    ``evidence`` and ``SQL`` (strings); ``difficulty`` (string) is optional.
    Other fields are ignored.

    Raises:
        InputError: if the file is unreadable, is not a JSON array of objects,
            misses a required field, has a field of the wrong type, or repeats
            a ``question_id``.

    Example:
        >>> dataset = load_bird(Path("examples/bird-mini/dev.json"))
        >>> len(dataset.cases)
        432
    """
    items = as_array(parse_json(read_utf8(path), path))
    if items is None:
        raise InputError(
            path,
            "expected a JSON array of question objects",
            hint='BIRD files look like [{"question_id": 0, ...}, ...]',
        )

    cases: list[Case] = []
    first_seen: dict[str, int] = {}
    for index, item in enumerate(items):
        location = f"item {index}"
        case = _parse_case(item, path, location)
        if case.id in first_seen:
            raise InputError(
                path,
                f"question_id {case.id} is repeated (first at item {first_seen[case.id]})",
                location=location,
                hint="every question_id must be unique",
            )
        first_seen[case.id] = index
        cases.append(case)
    return Dataset(path=path, cases=tuple(cases))


def load_bird_tied(path: Path, dataset: Dataset) -> dict[str, str]:
    """Read BIRD's tied-rows alternative gold file (``dev_tied_append.json``).

    The file has the same shape as the question file. Each entry gives, for an
    existing question, a gold SQL that returns every tied row instead of one.
    It is used only for flags, never for the verdict (ADR 0024).

    Returns:
        Alternative gold SQL by case id.

    Raises:
        InputError: for any problem ``load_bird`` reports, or an entry whose
            question is not in ``dataset`` or belongs to a different database.

    Example:
        >>> tied = load_bird_tied(Path("examples/bird-mini/dev_tied_append.json"), dataset)
        >>> len(tied)
        13
    """
    known = {case.id: case for case in dataset.cases}
    alternatives: dict[str, str] = {}
    for index, entry in enumerate(load_bird(path).cases):
        location = f"item {index}"
        original = known.get(entry.id)
        if original is None:
            raise InputError(
                path,
                f"question_id {entry.id} is not in the dataset {dataset.path}",
                location=location,
                hint="use the tied file that belongs to the same dataset split",
            )
        if original.db_id != entry.db_id:
            raise InputError(
                path,
                f"question_id {entry.id} is for database '{entry.db_id}', "
                f"but the dataset has it for '{original.db_id}'",
                location=location,
            )
        alternatives[entry.id] = entry.gold_sql
    return alternatives


def _parse_case(item: object, path: Path, location: str) -> Case:
    obj = as_object(item)
    if obj is None:
        raise InputError(
            path,
            f"expected a question object, found {json_type_name(item)}",
            location=location,
        )
    question_id = _require(obj, "question_id", int, path, location)
    difficulty = obj.get("difficulty")
    if difficulty is not None and not isinstance(difficulty, str):
        raise _wrong_type(path, location, "difficulty", "a string", difficulty)
    return Case(
        id=str(question_id),
        db_id=_require(obj, "db_id", str, path, location),
        question=_require(obj, "question", str, path, location),
        evidence=_require(obj, "evidence", str, path, location),
        gold_sql=_require(obj, "SQL", str, path, location),
        difficulty=difficulty,
    )


def _require(
    obj: dict[str, object],
    key: str,
    kind: type[_Scalar],
    path: Path,
    location: str,
) -> _Scalar:
    if key not in obj:
        raise InputError(
            path,
            f"missing field '{key}'",
            location=location,
            hint=f"add '{key}' to every question object",
        )
    value = obj[key]
    # bool is a subclass of int in Python, but true/false is never a valid id.
    if isinstance(value, kind) and not isinstance(value, bool):
        return value
    expected = "an integer" if kind is int else "a string"
    raise _wrong_type(path, location, key, expected, value)


def _wrong_type(
    path: Path, location: str, key: str, expected: str, value: object
) -> InputError:
    return InputError(
        path,
        f"field '{key}' must be {expected}, found {json_type_name(value)}",
        location=location,
    )
