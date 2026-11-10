"""Result-level classification of an incorrect case (ADR 0031).

Every incorrect case gets exactly one category, decided from the executed
results alone, so this needs no SQL parser and is always available.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Literal

from text2sql_eval.execution.executor import QueryFailure, QueryResult, Rows, SqlValue

ResultCategory = Literal[
    "execution_failed",
    "empty_result",
    "column_mismatch",
    "single_value_differs",
    "row_set_differs",
]

Relation = Literal["subset", "superset", "disjoint", "overlap"]

CATEGORY_LABELS_KO: dict[ResultCategory, str] = {
    "execution_failed": "실행 실패",
    "empty_result": "빈 결과",
    "column_mismatch": "컬럼 구성 차이",
    "single_value_differs": "값 하나가 다름",
    "row_set_differs": "행 집합 차이",
}

# Beyond this many predicted columns, trying every column subset to find the
# gold rows gets expensive (n! / (n-k)!); the hint is then left unknown.
_MAX_PROJECTION_COLUMNS = 8


@dataclass(frozen=True)
class ResultDiff:
    """Category plus hints that later feed false-incorrect flags.

    ``gold_contained`` says whether the gold rows appear unchanged inside the
    predicted rows: for ``column_mismatch``, after projecting the prediction
    onto some subset and order of its columns; for ``row_set_differs``, as a
    row subset. ``None`` means not applicable or not computed.
    ``relation`` compares the two row sets when the widths match.
    """

    category: ResultCategory
    gold_columns: int
    pred_columns: int
    gold_rows: int
    pred_rows: int
    gold_contained: bool | None = None
    relation: Relation | None = None


def classify(gold: QueryResult, pred: QueryResult) -> ResultDiff:
    """Classify an incorrect case. Callers only pass cases already judged incorrect.

    Example:
        >>> gold = Rows(("atom_id",), (("TR186_1",), ("TR186_10",)))
        >>> pred = Rows(("atom_id", "element"), (("TR186_1", "c"), ("TR186_10", "c")))
        >>> classify(gold, pred)
        ResultDiff(category='column_mismatch', gold_columns=1, pred_columns=2,
                   gold_rows=2, pred_rows=2, gold_contained=True, relation=None)
    """
    if isinstance(pred, QueryFailure) or isinstance(gold, QueryFailure):
        return ResultDiff(
            "execution_failed",
            gold_columns=_width(gold),
            pred_columns=_width(pred),
            gold_rows=_count(gold),
            pred_rows=_count(pred),
        )
    gold_set, pred_set = set(gold.rows), set(pred.rows)
    gold_columns, pred_columns = len(gold.columns), len(pred.columns)
    gold_rows, pred_rows = len(gold.rows), len(pred.rows)

    def diff(
        category: ResultCategory,
        *,
        gold_contained: bool | None = None,
        relation: Relation | None = None,
    ) -> ResultDiff:
        return ResultDiff(
            category,
            gold_columns=gold_columns,
            pred_columns=pred_columns,
            gold_rows=gold_rows,
            pred_rows=pred_rows,
            gold_contained=gold_contained,
            relation=relation,
        )

    if not pred.rows and gold.rows:
        return diff("empty_result")
    if gold_columns != pred_columns:
        return diff("column_mismatch", gold_contained=_projects_onto(pred, gold_set))
    if len(gold_set) == 1 and len(pred_set) == 1 and gold_columns == 1:
        return diff("single_value_differs")
    relation: Relation
    if pred_set < gold_set:
        relation = "subset"
    elif pred_set > gold_set:
        relation = "superset"
    elif pred_set & gold_set:
        relation = "overlap"
    else:
        relation = "disjoint"
    return diff(
        "row_set_differs", gold_contained=relation == "superset", relation=relation
    )


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


def _count(result: QueryResult) -> int:
    return len(result.rows) if isinstance(result, Rows) else 0
