"""One CSV row per case of a run, for spreadsheet analysis (ADR 0007).

Researchers used to classify wrong cases by hand in a spreadsheet. This file
starts that sheet with the verdict, the differences and the flags already
filled in, and leaves ``my_category`` and ``notes`` empty for the user.
"""

from __future__ import annotations

import csv
from pathlib import Path

from text2sql_eval.judge.ex import ExecError, Verdict, status_of
from text2sql_eval.runfile import CaseRecord, Run

CSV_COLUMNS = (
    "id",
    "db_id",
    "difficulty",
    "status",
    "prediction",
    "output_differences",
    "sql_structure_differences",
    "flags",
    "question",
    "evidence",
    "gold_sql",
    "pred_sql",
    "error",
    "my_category",
    "notes",
)


def write_csv(run: Run, path: Path) -> None:
    """Write every case of ``run`` as one CSV row, in the run's order.

    Written as UTF-8 with a byte order mark so Excel shows Korean text and
    other non-ASCII characters correctly. Multiple differences or flags are
    joined with ``;``. ``prediction`` is ``given``, ``empty`` or ``missing``.

    Example:
        >>> write_csv(read_run(Path("runs/v3.json")), Path("runs/v3.csv"))
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_COLUMNS)
        for case in run.cases:
            writer.writerow(_row(case))


def _row(case: CaseRecord) -> tuple[str, ...]:
    outputs = () if case.diff is None else case.diff.output.differences
    facts = () if case.diff is None else case.diff.structure.facts
    return (
        case.id,
        case.db_id,
        case.difficulty or "",
        status_of(case.verdict),
        case.prediction_state,
        ";".join(outputs),
        ";".join(fact.kind for fact in facts),
        ";".join(flag.kind for flag in case.verdict.flags),
        case.question,
        case.evidence,
        case.gold_sql,
        case.pred_sql,
        _error(case.verdict),
        "",
        "",
    )


def _error(verdict: Verdict) -> str:
    if isinstance(verdict, ExecError):
        return f"{verdict.side} {verdict.kind}: {verdict.message}"
    return ""
