"""A single-file HTML report of one run (ADR 0007, 0038, 0039).

The page works offline: the CSS and the small filter script are inline and
nothing is loaded from the network. Every value goes through Jinja2 with
autoescaping on, so text from questions, SQL and results is shown as text,
never interpreted as HTML.

The template only displays. Everything it shows is prepared here as strings
in small dataclasses, which pyright checks; the template has no logic beyond
loops and ``if``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

import jinja2

# sqlglot 30's node base class; see the note in facts/structure.py.
from sqlglot.expressions.core import Expr

from text2sql_eval.execution.executor import QueryFailure, SqlValue
from text2sql_eval.facts.output import OUTPUT_LABELS_KO, OutputDiff, Relation
from text2sql_eval.facts.structure import DIALECT, STRUCTURE_LABELS_KO, parse
from text2sql_eval.judge.ex import ExecError, FlagKind, Verdict, status_of
from text2sql_eval.report.highlight import (
    Clause,
    clause_blocks,
    differing_clauses,
    differing_rows,
)
from text2sql_eval.runfile import CaseRecord, QuerySummary, Run

# A bound TypeVar instead of 3.12's ``def f[K: str]`` (ADR 0009).
_Kind = TypeVar("_Kind", bound=str)

FlagGroup = Literal["suspect_correct", "suspect_incorrect", "info"]

FLAG_LABELS_KO: dict[FlagKind, str] = {
    "empty_prediction_correct": "빈 예측이 정답 처리됨",
    "gold_empty_correct": "정답 결과가 비어, 결과가 비기만 하면 정답 처리됨",
    "matches_tied_alternative_only": "동점 대체 정답과만 일치",
    "gold_rows_with_extra_columns": "정답 행을 그대로 포함하고 컬럼만 더 있음",
    "gold_columns_concatenated": "정답의 여러 컬럼을 한 문자열로 이어 붙임",
    "tied_alternative_exists": "동점 대체 정답이 있는 문제",
}

# The three groups of ADR 0034.
FLAG_GROUPS: dict[FlagKind, FlagGroup] = {
    "empty_prediction_correct": "suspect_correct",
    "gold_empty_correct": "suspect_correct",
    "matches_tied_alternative_only": "suspect_incorrect",
    "gold_rows_with_extra_columns": "suspect_incorrect",
    "gold_columns_concatenated": "suspect_incorrect",
    "tied_alternative_exists": "info",
}

FLAG_GROUP_LABELS_KO: dict[FlagGroup, str] = {
    "suspect_correct": "거짓 정답 의심",
    "suspect_incorrect": "거짓 오답 의심",
    "info": "정보",
}

_STATUS_LABELS_KO = {"correct": "정답", "incorrect": "오답", "error": "오류"}

_PREDICTION_LABELS_KO = {
    "given": "",
    "empty": "빈 예측",
    "missing": "예측 없음 (빈 SQL로 판정)",
}

_RELATION_LABELS_KO: dict[Relation, str] = {
    "subset": "예측 행이 모두 정답에 있음 (정답의 일부만 반환)",
    "superset": "정답 행을 모두 포함하고 행이 더 있음",
    "overlap": "일부 행만 겹침",
    "disjoint": "겹치는 행이 없음",
}

_DIFFICULTY_ORDER = {"simple": 0, "moderate": 1, "challenging": 2}

# Bytes values are shown as a SQL hex literal, cut after this many bytes.
_MAX_BYTES_SHOWN = 16


# --- what the template shows ------------------------------------------------


@dataclass(frozen=True)
class Labeled:
    """A code such as ``empty_result`` and its Korean description."""

    code: str
    label: str


@dataclass(frozen=True)
class CountRow:
    code: str
    label: str
    count: int


@dataclass(frozen=True)
class GroupRow:
    """EX of one difficulty or database."""

    name: str
    cases: int
    correct: int
    ex: str


@dataclass(frozen=True)
class SqlBlock:
    """Lines of formatted SQL; ``differs`` marks a clause to highlight."""

    text: str
    differs: bool = False


@dataclass(frozen=True)
class SqlView:
    """SQL formatted for reading, with the original text kept alongside.

    ``blocks`` is empty when there is no SQL. ``formatted`` is false when
    sqlglot could not parse the SQL, so it is shown as written.
    """

    blocks: tuple[SqlBlock, ...]
    original: str
    formatted: bool


@dataclass(frozen=True)
class Cell:
    text: str
    null: bool = False


@dataclass(frozen=True)
class RowView:
    cells: tuple[Cell, ...]
    differs: bool = False


@dataclass(frozen=True)
class TableView:
    """The stored sample of one query result, or why the query failed."""

    columns: tuple[str, ...]
    rows: tuple[RowView, ...]
    caption: str
    failure: str | None = None


@dataclass(frozen=True)
class FactView:
    code: str
    label: str
    gold: str
    pred: str


@dataclass(frozen=True)
class FlagView:
    code: str
    label: str
    group: FlagGroup
    group_label: str
    detail: str


@dataclass(frozen=True)
class NumberRow:
    """One measured quantity of both results, e.g. the number of columns."""

    label: str
    gold: int
    pred: int


@dataclass(frozen=True)
class CaseView:
    id: str
    db_id: str
    difficulty: str
    status: str
    status_label: str
    prediction_label: str
    question: str
    evidence: str
    gold_sql: SqlView
    pred_sql: SqlView
    error: str
    outputs: tuple[Labeled, ...]
    numbers: tuple[NumberRow, ...]
    relation: str
    facts: tuple[FactView, ...]
    structure_note: str
    flags: tuple[FlagView, ...]
    gold_result: TableView
    pred_result: TableView
    filters: dict[str, str]
    """Space-separated tokens per filter key, read by the filter script."""


@dataclass(frozen=True)
class FilterOption:
    value: str
    label: str


@dataclass(frozen=True)
class Filter:
    key: str
    label: str
    options: tuple[FilterOption, ...]
    default: str = ""


@dataclass(frozen=True)
class Page:
    title: str
    info: tuple[tuple[str, str], ...]
    ex: str
    status_counts: tuple[CountRow, ...]
    by_difficulty: tuple[GroupRow, ...]
    by_db: tuple[GroupRow, ...]
    output_counts: tuple[CountRow, ...]
    structure_counts: tuple[CountRow, ...]
    flag_counts: tuple[CountRow, ...]
    filters: tuple[Filter, ...]
    cases: tuple[CaseView, ...]


# --- rendering ----------------------------------------------------------------


def write_html_report(run: Run, path: Path, *, run_name: str) -> None:
    """Write the report of ``run`` to ``path`` as one UTF-8 HTML file.

    ``run_name`` names the run in the page title, usually the run file name.

    Example:
        >>> run_path = Path("runs/v3.json")
        >>> write_html_report(read_run(run_path), Path("runs/v3.html"), run_name=run_path.name)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(run, run_name=run_name), encoding="utf-8")


def render_html(run: Run, *, run_name: str) -> str:
    """The report of ``run`` as an HTML document."""
    environment = jinja2.Environment(
        loader=jinja2.PackageLoader("text2sql_eval.report", "templates"),
        autoescape=True,
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template("report.html.j2")
    return template.render(page=build_page(run, run_name=run_name))


def build_page(run: Run, *, run_name: str) -> Page:
    """Everything the template shows, computed from the run."""
    cases = tuple(_case_view(case) for case in run.cases)
    summary = run.summary
    return Page(
        title=f"text2sql-eval report: {run_name}",
        info=_info(run, run_name),
        ex=f"{summary.ex:.1%}",
        status_counts=(
            CountRow("total", "전체", summary.total),
            CountRow("correct", "정답", summary.correct),
            CountRow("incorrect", "오답", summary.incorrect),
            CountRow("error", "오류", summary.error),
        ),
        by_difficulty=_groups(
            run.cases, lambda c: c.difficulty or "(없음)", _difficulty_key
        ),
        by_db=_groups(run.cases, lambda c: c.db_id, lambda name: (0, name)),
        output_counts=_count_rows(_output_kinds(run.cases), OUTPUT_LABELS_KO),
        structure_counts=_count_rows(_structure_kinds(run.cases), STRUCTURE_LABELS_KO),
        flag_counts=_flag_counts(run.cases),
        filters=_filters(run.cases),
        cases=cases,
    )


# --- summary ------------------------------------------------------------------


def _info(run: Run, run_name: str) -> tuple[tuple[str, str], ...]:
    rows = [
        ("실행 파일", run_name),
        ("만든 시각", run.created_at),
        ("도구 버전", run.tool_version),
        ("데이터셋", run.dataset.path),
        ("예측 파일", f"{run.predictions.path} ({run.prediction_format})"),
        ("동점 대체 정답", "없음" if run.tied is None else run.tied.path),
        ("시간 제한", f"쿼리당 {run.settings.timeout_seconds:g}초"),
    ]
    rows.extend((f"meta: {key}", value) for key, value in sorted(run.meta.items()))
    return tuple(rows)


def _difficulty_key(name: str) -> tuple[int, str]:
    return (_DIFFICULTY_ORDER.get(name, len(_DIFFICULTY_ORDER)), name)


def _groups(
    cases: Iterable[CaseRecord],
    name_of: Callable[[CaseRecord], str],
    sort_key: Callable[[str], tuple[int, str]],
) -> tuple[GroupRow, ...]:
    totals: Counter[str] = Counter()
    correct: Counter[str] = Counter()
    for case in cases:
        name = name_of(case)
        totals[name] += 1
        correct[name] += status_of(case.verdict) == "correct"
    return tuple(
        GroupRow(
            name, totals[name], correct[name], f"{correct[name] / totals[name]:.1%}"
        )
        for name in sorted(totals, key=sort_key)
    )


def _output_kinds(cases: Iterable[CaseRecord]) -> Counter[str]:
    return Counter(
        kind for case in cases if case.diff for kind in case.diff.output.differences
    )


def _structure_kinds(cases: Iterable[CaseRecord]) -> Counter[str]:
    return Counter(
        fact.kind for case in cases if case.diff for fact in case.diff.structure.facts
    )


def _count_rows(
    counts: Counter[str], labels: Mapping[_Kind, str]
) -> tuple[CountRow, ...]:
    """Every kind in ``labels``, most frequent first, ties in ``labels`` order.

    Kinds that never occur are kept, with count 0, at the end.
    """
    kinds = list(labels)
    ordered = sorted(kinds, key=lambda kind: (-counts[kind], kinds.index(kind)))
    return tuple(CountRow(kind, labels[kind], counts[kind]) for kind in ordered)


def _flag_counts(cases: Iterable[CaseRecord]) -> tuple[CountRow, ...]:
    """Every flag kind in the order of ADR 0034, including those never raised."""
    counts = Counter(flag.kind for case in cases for flag in case.verdict.flags)
    return tuple(
        CountRow(
            kind,
            f"{FLAG_GROUP_LABELS_KO[FLAG_GROUPS[kind]]}: {FLAG_LABELS_KO[kind]}",
            counts[kind],
        )
        for kind in FLAG_LABELS_KO
    )


def _filters(cases: tuple[CaseRecord, ...]) -> tuple[Filter, ...]:
    everything = FilterOption("", "전체")
    databases = sorted({case.db_id for case in cases})
    difficulties = sorted(
        {case.difficulty or "none" for case in cases}, key=_difficulty_key
    )
    outputs = _output_kinds(cases)
    structures = _structure_kinds(cases)
    flags = Counter(flag.kind for case in cases for flag in case.verdict.flags)
    return (
        Filter(
            "status",
            "판정",
            (
                everything,
                FilterOption("wrong", "오답·오류"),
                FilterOption("correct", "정답"),
                FilterOption("incorrect", "오답"),
                FilterOption("error", "오류"),
            ),
            default="wrong",
        ),
        Filter(
            "db",
            "데이터베이스",
            (everything, *(FilterOption(db, db) for db in databases)),
        ),
        Filter(
            "difficulty",
            "난이도",
            (
                everything,
                *(
                    FilterOption(d, "(없음)" if d == "none" else d)
                    for d in difficulties
                ),
            ),
        ),
        Filter(
            "output",
            "출력 차이",
            (
                everything,
                *(
                    FilterOption(row.code, f"{row.code} ({row.label}) {row.count}")
                    for row in _count_rows(outputs, OUTPUT_LABELS_KO)
                    if row.count
                ),
            ),
        ),
        Filter(
            "structure",
            "SQL 구조 차이",
            (
                everything,
                *(
                    FilterOption(row.code, f"{row.code} ({row.label}) {row.count}")
                    for row in _count_rows(structures, STRUCTURE_LABELS_KO)
                    if row.count
                ),
            ),
        ),
        Filter(
            "flag",
            "플래그",
            (
                everything,
                *(
                    FilterOption(group, f"{label} (모두)")
                    for group, label in FLAG_GROUP_LABELS_KO.items()
                    if group != "info"
                ),
                *(
                    FilterOption(kind, f"{kind} {flags[kind]}")
                    for kind in FLAG_LABELS_KO
                    if flags[kind]
                ),
            ),
        ),
    )


# --- one case -----------------------------------------------------------------


def _case_view(case: CaseRecord) -> CaseView:
    status = status_of(case.verdict)
    diff = case.diff
    flags = tuple(
        FlagView(
            code=flag.kind,
            label=FLAG_LABELS_KO[flag.kind],
            group=FLAG_GROUPS[flag.kind],
            group_label=FLAG_GROUP_LABELS_KO[FLAG_GROUPS[flag.kind]],
            detail=flag.detail,
        )
        for flag in case.verdict.flags
    )
    outputs = () if diff is None else diff.output.differences
    facts = () if diff is None else diff.structure.facts
    # Highlight where the differences are reported: cases that are not
    # correct and whose gold query ran (ADR 0031, 0039).
    highlight = diff is not None
    gold_sql, pred_sql = sql_views(case.gold_sql, case.pred_sql, highlight=highlight)
    gold_rows, pred_rows = (
        differing_rows(case.gold, case.pred) if highlight else ((), ())
    )
    return CaseView(
        id=case.id,
        db_id=case.db_id,
        difficulty=case.difficulty or "",
        status=status,
        status_label=_STATUS_LABELS_KO[status],
        prediction_label=_PREDICTION_LABELS_KO[case.prediction_state],
        question=case.question,
        evidence=case.evidence,
        gold_sql=gold_sql,
        pred_sql=pred_sql,
        error=_error(case.verdict),
        outputs=tuple(Labeled(kind, OUTPUT_LABELS_KO[kind]) for kind in outputs),
        numbers=() if diff is None else _numbers(diff.output),
        relation=""
        if diff is None or diff.output.relation is None
        else _RELATION_LABELS_KO[diff.output.relation],
        facts=tuple(
            FactView(fact.kind, STRUCTURE_LABELS_KO[fact.kind], fact.gold, fact.pred)
            for fact in facts
        ),
        structure_note=_structure_note(case),
        flags=flags,
        gold_result=table_view(case.gold, gold_rows),
        pred_result=table_view(case.pred, pred_rows),
        filters={
            "status": status if status == "correct" else f"{status} wrong",
            "db": case.db_id,
            "difficulty": case.difficulty or "none",
            "output": " ".join(outputs),
            "structure": " ".join(fact.kind for fact in facts),
            "flag": " ".join(
                sorted({flag.code for flag in flags} | {flag.group for flag in flags})
            ),
        },
    )


def sql_views(
    gold_sql: str, pred_sql: str, *, highlight: bool
) -> tuple[SqlView, SqlView]:
    """Both queries reformatted by sqlglot, one block per outer clause.

    With ``highlight``, clauses that differ between the two are marked. SQL
    that is empty or that sqlglot cannot parse is shown as written, and then
    nothing is marked on either side.
    """
    gold_tree = parse(gold_sql) if gold_sql.strip() else None
    pred_tree = parse(pred_sql) if pred_sql.strip() else None
    differs: frozenset[Clause] = frozenset()
    if highlight and gold_tree is not None and pred_tree is not None:
        differs = differing_clauses(gold_tree, pred_tree)
    return (
        _sql_view(gold_sql, gold_tree, differs),
        _sql_view(pred_sql, pred_tree, differs),
    )


def _sql_view(sql: str, tree: Expr | None, differs: frozenset[Clause]) -> SqlView:
    if not sql.strip():
        return SqlView((), sql, formatted=False)
    if tree is None:
        return SqlView((SqlBlock(sql.strip()),), sql, formatted=False)
    pretty = tree.sql(dialect=DIALECT, pretty=True)
    return SqlView(
        tuple(
            SqlBlock(text, differs=clause in differs)
            for clause, text in clause_blocks(pretty)
        ),
        sql,
        formatted=True,
    )


def table_view(result: QuerySummary, differs: tuple[bool, ...] = ()) -> TableView:
    """A result sample as a table; ``differs`` marks rows, one flag per row."""
    if isinstance(result, QueryFailure):
        return TableView((), (), caption="", failure=f"{result.kind}: {result.message}")
    if result.row_count > len(result.rows):
        caption = f"앞 {len(result.rows)}행 / 전체 {result.row_count}행"
    else:
        caption = f"{result.row_count}행"
    return TableView(
        columns=result.columns,
        rows=tuple(
            RowView(
                tuple(_cell(value) for value in row),
                differs=index < len(differs) and differs[index],
            )
            for index, row in enumerate(result.rows)
        ),
        caption=caption,
    )


def _cell(value: SqlValue) -> Cell:
    if value is None:
        return Cell("NULL", null=True)
    if isinstance(value, bytes):
        shown = value[:_MAX_BYTES_SHOWN].hex()
        more = "…" if len(value) > _MAX_BYTES_SHOWN else ""
        return Cell(f"x'{shown}{more}' ({len(value)} bytes)")
    return Cell(str(value))


def _numbers(output: OutputDiff) -> tuple[NumberRow, ...]:
    return (
        NumberRow("컬럼 수", output.gold_columns, output.pred_columns),
        NumberRow(
            "서로 다른 행 수", output.gold_distinct_rows, output.pred_distinct_rows
        ),
    )


def _structure_note(case: CaseRecord) -> str:
    if case.diff is None:
        return ""
    failed = case.diff.structure.parse_failed
    if failed is not None:
        side = "정답" if failed == "gold" else "예측"
        return f"{side} SQL을 파싱하지 못해 구조 차이를 구하지 않았습니다."
    if not case.diff.structure.facts:
        return "비교하는 다섯 가지 구조에서는 차이를 찾지 못했습니다."
    return ""


def _error(verdict: Verdict) -> str:
    if not isinstance(verdict, ExecError):
        return ""
    side = "예측" if verdict.side == "pred" else "정답"
    return f"{side} SQL 실행 실패 ({verdict.kind}): {verdict.message}"
