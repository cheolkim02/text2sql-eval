"""Judge execution accuracy (EX) exactly as BIRD's official script does.

The official rule is ``set(predicted_rows) == set(gold_rows)``: row order and
duplicate rows are ignored, the order of values inside a row matters, column
names are ignored, and values compare with Python ``==`` (so ``1 == 1.0``).
A query that fails scores zero (ADR 0022).

Weaknesses of that rule are surfaced as flags, never by changing the verdict
(ADR 0023, ADR 0024).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, assert_never

from text2sql_eval.execution.executor import QueryFailure, QueryResult, Rows, SqlValue
from text2sql_eval.facts.output import (
    concatenates_gold_columns,
    gold_rows_in_projection,
)

FlagKind = Literal[
    "empty_prediction_correct",
    "gold_empty_correct",
    "matches_tied_alternative_only",
    "gold_rows_with_extra_columns",
    "gold_columns_concatenated",
    "tied_alternative_exists",
]


@dataclass(frozen=True)
class Flag:
    """A reason to doubt or double-check a verdict. It never changes the verdict."""

    kind: FlagKind
    detail: str


@dataclass(frozen=True)
class Correct:
    """The prediction's rows equal the gold rows as sets."""

    flags: tuple[Flag, ...] = ()


@dataclass(frozen=True)
class Incorrect:
    """Both queries ran, and their rows differ as sets."""

    flags: tuple[Flag, ...] = ()


@dataclass(frozen=True)
class ExecError:
    """A query failed, so the case scores zero.

    ``side`` says whose query failed. When both fail, the prediction is
    reported, because the official script runs it first.
    """

    side: Literal["pred", "gold"]
    kind: Literal["error", "timeout", "row_limit"]
    message: str
    flags: tuple[Flag, ...] = ()


Verdict = Correct | Incorrect | ExecError

_EMPTY_PREDICTION_CORRECT = Flag(
    "empty_prediction_correct",
    "the model gave no SQL; it counts as correct only because the gold result "
    "is empty too",
)
_GOLD_EMPTY_CORRECT = Flag(
    "gold_empty_correct",
    "the gold result is empty, so any query returning no rows counts as correct",
)
_GOLD_ROWS_WITH_EXTRA_COLUMNS = Flag(
    "gold_rows_with_extra_columns",
    "the prediction returns every gold row plus extra columns; it may be a "
    "correct answer judged wrong",
)
_GOLD_COLUMNS_CONCATENATED = Flag(
    "gold_columns_concatenated",
    "the prediction joins the gold columns into one text column; it may be a "
    "correct answer in a different format",
)
_TIED_ALTERNATIVE_EXISTS = Flag(
    "tied_alternative_exists",
    "the dataset has an alternative gold SQL that returns all tied rows; "
    "the original gold picks only some of them",
)
_MATCHES_TIED_ALTERNATIVE_ONLY = Flag(
    "matches_tied_alternative_only",
    "the prediction matches the tied-rows alternative gold but not the "
    "original gold; it may be a correct answer judged wrong",
)


def official_match(
    pred_rows: Sequence[tuple[SqlValue, ...]], gold_rows: Sequence[tuple[SqlValue, ...]]
) -> bool:
    """BIRD's comparison, verbatim: ``set(predicted_res) == set(ground_truth_res)``."""
    return set(pred_rows) == set(gold_rows)


def judge_case(
    gold: QueryResult,
    pred: QueryResult,
    *,
    pred_is_empty: bool,
    tied: QueryResult | None = None,
) -> Verdict:
    """Judge one case from the executed gold and predicted queries.

    Args:
        gold: Result of the gold SQL.
        pred: Result of the predicted SQL. An empty or missing prediction is
            executed as empty SQL, like the official script does.
        pred_is_empty: Whether the model gave no SQL (ADR 0023).
        tied: Result of the tied-rows alternative gold SQL, if the dataset has
            one for this case (ADR 0024).

    Example:
        >>> gold = Rows(columns=("n",), rows=((1,), (2,)))
        >>> judge_case(gold, Rows(columns=("x",), rows=((2,), (1,), (1,))), pred_is_empty=False)
        Correct(flags=())
    """
    flags: list[Flag] = []
    if tied is not None:
        flags.append(_TIED_ALTERNATIVE_EXISTS)

    # The official script runs the prediction first, so its failure wins.
    if isinstance(pred, QueryFailure):
        return ExecError("pred", pred.kind, pred.message, tuple(flags))
    if isinstance(gold, QueryFailure):
        return ExecError("gold", gold.kind, gold.message, tuple(flags))

    if official_match(pred.rows, gold.rows):
        if pred_is_empty:
            flags.append(_EMPTY_PREDICTION_CORRECT)
        elif not gold.rows:
            flags.append(_GOLD_EMPTY_CORRECT)
        return Correct(flags=tuple(flags))

    if isinstance(tied, Rows) and official_match(pred.rows, tied.rows):
        flags.append(_MATCHES_TIED_ALTERNATIVE_ONLY)
    gold_set = set(gold.rows)
    if (
        gold_set
        and len(pred.columns) > len(gold.columns)
        and gold_rows_in_projection(gold_set, pred) is True
    ):
        flags.append(_GOLD_ROWS_WITH_EXTRA_COLUMNS)
    if concatenates_gold_columns(gold, pred):
        flags.append(_GOLD_COLUMNS_CONCATENATED)
    return Incorrect(flags=tuple(flags))


def status_of(verdict: Verdict) -> Literal["correct", "incorrect", "error"]:
    """The verdict's status name, as written to run files and reports."""
    match verdict:
        case Correct():
            return "correct"
        case Incorrect():
            return "incorrect"
        case ExecError():
            return "error"
        case _:
            # pyright proves this unreachable; a new Verdict type fails here.
            assert_never(verdict)
