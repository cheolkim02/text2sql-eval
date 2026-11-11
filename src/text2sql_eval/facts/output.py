"""Output differences of a wrong case: how its result differs from gold (ADR 0033).

Each check looks at one aspect of the executed results, so a case can have
several differences at once (for example a different row count and different
rows). Decided from executed rows alone, so no SQL parser is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Literal

from text2sql_eval.execution.executor import QueryFailure, QueryResult, Rows, SqlValue

OutputDifference = Literal[
    "execution_failed",
    "empty_result",
    "column_mismatch",
    "row_count_differs",
    "single_value_differs",
    "row_set_differs",
]

Relation = Literal["subset", "superset", "disjoint", "overlap"]

OUTPUT_LABELS_KO: dict[OutputDifference, str] = {
    "execution_failed": "실행 실패",
    "empty_result": "빈 결과",
    "column_mismatch": "컬럼 수가 다름",
    "row_count_differs": "행 수가 다름",
    "single_value_differs": "값 하나가 다름",
    "row_set_differs": "행 내용이 다름",
}

# Beyond this many predicted columns, trying every column subset to find the
# gold rows gets expensive (n! / (n-k)!); the hint is then left unknown.
_MAX_PROJECTION_COLUMNS = 8


@dataclass(frozen=True)
class OutputDiff:
    """All output differences of one wrong case, plus hints for later flags.

    Row counts are distinct rows, because EX compares rows as sets.
    ``gold_contained`` says whether the gold rows appear unchanged inside the
    predicted rows (after projecting onto some subset and order of the
    predicted columns when the widths differ); ``None`` means not applicable
    or not computed. ``relation`` compares the row sets when widths match.
    """

    differences: tuple[OutputDifference, ...]
    gold_columns: int
    pred_columns: int
    gold_distinct_rows: int
    pred_distinct_rows: int
    gold_contained: bool | None = None
    relation: Relation | None = None


def compare_outputs(gold: QueryResult, pred: QueryResult) -> OutputDiff:
    """Every output difference of a case already judged not correct.

    - ``execution_failed``: a query failed; no other check is possible.
    - ``empty_result``: the prediction returned no rows but gold did; checks of
      row content are then moot, only ``column_mismatch`` can join it.
    - ``column_mismatch``: the number of columns differs.
    - ``row_count_differs``: the number of distinct rows differs.
    - ``single_value_differs``: both results are one value (one row, one
      column) and the values differ.
    - ``row_set_differs``: the rows differ. With equal widths, the row sets
      differ; with different widths, the gold rows are not found inside the
      predicted rows under any column projection.

    Example:
        >>> gold = Rows(("name",), (("Surtur",),))
        >>> pred = Rows(("name",), (("Surtur",), ("Ymir",)))
        >>> compare_outputs(gold, pred).differences
        ('row_count_differs', 'row_set_differs')
    """
    if isinstance(pred, QueryFailure) or isinstance(gold, QueryFailure):
        return OutputDiff(
            ("execution_failed",),
            gold_columns=_width(gold),
            pred_columns=_width(pred),
            gold_distinct_rows=_distinct(gold),
            pred_distinct_rows=_distinct(pred),
        )
    gold_set, pred_set = set(gold.rows), set(pred.rows)
    gold_width, pred_width = len(gold.columns), len(pred.columns)
    found: list[OutputDifference] = []
    contained: bool | None = None
    relation: Relation | None = None

    if gold_set and not pred_set:
        found.append("empty_result")
        # Zero columns only comes from empty SQL (no prediction); comparing
        # column counts would call a missing answer a "column" problem.
        if pred_width and gold_width != pred_width:
            found.append("column_mismatch")
    else:
        if gold_width != pred_width:
            found.append("column_mismatch")
            contained = _projects_onto(pred, gold_set)
        else:
            relation = _relation(gold_set, pred_set)
            contained = relation == "superset"
        if not gold_set:
            contained = (
                None  # "gold rows are contained" says nothing when there are none
            )
        if len(gold_set) != len(pred_set):
            found.append("row_count_differs")
        if _single_value(gold, gold_set) and _single_value(pred, pred_set):
            found.append("single_value_differs")
        elif gold_width == pred_width and gold_set != pred_set:
            found.append("row_set_differs")
        elif gold_width != pred_width and contained is False:
            # None (too many columns to check) claims nothing about the rows.
            found.append("row_set_differs")

    return OutputDiff(
        tuple(found),
        gold_columns=gold_width,
        pred_columns=pred_width,
        gold_distinct_rows=len(gold_set),
        pred_distinct_rows=len(pred_set),
        gold_contained=contained,
        relation=relation,
    )


def _single_value(result: Rows, distinct: set[tuple[SqlValue, ...]]) -> bool:
    return len(result.columns) == 1 and len(distinct) == 1


def _relation(
    gold_set: set[tuple[SqlValue, ...]], pred_set: set[tuple[SqlValue, ...]]
) -> Relation | None:
    if pred_set == gold_set:
        return None
    if pred_set < gold_set:
        return "subset"
    if pred_set > gold_set:
        return "superset"
    if pred_set & gold_set:
        return "overlap"
    return "disjoint"


def _projects_onto(pred: Rows, gold_set: set[tuple[SqlValue, ...]]) -> bool | None:
    """Whether some subset and order of ``pred``'s columns gives exactly the gold rows."""
    width = len(pred.columns)
    gold_width = len(next(iter(gold_set), ()))
    if gold_width == 0 or gold_width > width:
        return False
    if width > _MAX_PROJECTION_COLUMNS:
        return None
    for columns in permutations(range(width), gold_width):
        projected = {tuple(row[index] for index in columns) for row in pred.rows}
        if projected == gold_set:
            return True
    return False


def _width(result: QueryResult) -> int:
    return len(result.columns) if isinstance(result, Rows) else 0


def _distinct(result: QueryResult) -> int:
    return len(set(result.rows)) if isinstance(result, Rows) else 0
