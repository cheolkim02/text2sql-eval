"""Compare two runs case by case (ADR 0035, 0036, 0037).

What a researcher used to do in a spreadsheet: which cases both runs got
right, which only one got right, and how the kinds of mistakes changed.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from text2sql_eval.csv_safety import excel_safe
from text2sql_eval.judge.ex import status_of
from text2sql_eval.runfile import CaseRecord, Run

Change = Literal["both_correct", "fixed", "regressed", "both_wrong"]

CHANGE_LABELS_KO: dict[Change, str] = {
    "both_correct": "둘 다 맞음",
    "fixed": "head만 맞음 (고쳐짐)",
    "regressed": "base만 맞음 (나빠짐)",
    "both_wrong": "둘 다 틀림",
}


@dataclass(frozen=True)
class CaseChange:
    """One case seen in both runs."""

    base: CaseRecord
    head: CaseRecord

    @property
    def change(self) -> Change:
        base_ok = status_of(self.base.verdict) == "correct"
        head_ok = status_of(self.head.verdict) == "correct"
        if base_ok and head_ok:
            return "both_correct"
        if head_ok:
            return "fixed"
        if base_ok:
            return "regressed"
        return "both_wrong"


@dataclass(frozen=True)
class GroupEx:
    """EX of both runs over the common cases of one group (e.g. a difficulty)."""

    name: str
    cases: int
    base_ex: float
    head_ex: float


@dataclass(frozen=True)
class Comparison:
    """Two runs compared over the cases they share, in the base run's order."""

    cases: tuple[CaseChange, ...]
    dataset_mismatch: bool
    only_in_base: tuple[str, ...]
    only_in_head: tuple[str, ...]

    def counts(self) -> Counter[Change]:
        return Counter(case.change for case in self.cases)

    @property
    def base_ex(self) -> float:
        return _ex([c.base for c in self.cases])

    @property
    def head_ex(self) -> float:
        return _ex([c.head for c in self.cases])

    @property
    def delta_pp(self) -> float:
        """Change in EX, in percentage points (head minus base)."""
        return (self.head_ex - self.base_ex) * 100

    def by(self, key: Literal["difficulty", "db_id"]) -> list[GroupEx]:
        """EX per difficulty or per database, groups in name order."""
        groups: dict[str, list[CaseChange]] = {}
        for case in self.cases:
            value = case.base.difficulty if key == "difficulty" else case.base.db_id
            groups.setdefault(value or "(none)", []).append(case)
        return [
            GroupEx(
                name=name,
                cases=len(members),
                base_ex=_ex([m.base for m in members]),
                head_ex=_ex([m.head for m in members]),
            )
            for name, members in sorted(groups.items())
        ]

    def output_differences(self) -> tuple[Counter[str], Counter[str]]:
        """Counts of each output difference kind in base and in head."""
        return (
            Counter(d for c in self.cases for d in _outputs(c.base)),
            Counter(d for c in self.cases for d in _outputs(c.head)),
        )

    def structure_differences(self) -> tuple[Counter[str], Counter[str]]:
        """Counts of each SQL structure difference kind in base and in head."""
        return (
            Counter(f for c in self.cases for f in _structures(c.base)),
            Counter(f for c in self.cases for f in _structures(c.head)),
        )


def compare_runs(base: Run, head: Run) -> Comparison:
    """Pair up the cases two runs share; note what only one of them has.

    A different dataset hash is reported, not refused (ADR 0037); callers show
    it as a warning.

    Example:
        >>> comparison = compare_runs(read_run(no_evidence), read_run(evidence))
        >>> comparison.counts()["fixed"], round(comparison.delta_pp, 1)
        (123, 24.3)
    """
    head_by_id = {case.id: case for case in head.cases}
    base_ids = {case.id for case in base.cases}
    pairs = tuple(
        CaseChange(base=case, head=head_by_id[case.id])
        for case in base.cases
        if case.id in head_by_id
    )
    return Comparison(
        cases=pairs,
        dataset_mismatch=base.dataset.sha256 != head.dataset.sha256,
        only_in_base=tuple(c.id for c in base.cases if c.id not in head_by_id),
        only_in_head=tuple(c.id for c in head.cases if c.id not in base_ids),
    )


def _ex(records: list[CaseRecord]) -> float:
    if not records:
        return 0.0
    return sum(status_of(r.verdict) == "correct" for r in records) / len(records)


def _outputs(record: CaseRecord) -> tuple[str, ...]:
    return () if record.diff is None else record.diff.output.differences


def _structures(record: CaseRecord) -> tuple[str, ...]:
    if record.diff is None:
        return ()
    return tuple(fact.kind for fact in record.diff.structure.facts)


CSV_COLUMNS = (
    "id",
    "db_id",
    "difficulty",
    "change",
    "base_status",
    "head_status",
    "base_output_differences",
    "head_output_differences",
    "question",
    "gold_sql",
    "base_pred_sql",
    "head_pred_sql",
)


def write_csv(comparison: Comparison, path: Path) -> None:
    """One row per common case, for spreadsheet analysis.

    Written as UTF-8 with a byte order mark so Excel shows Korean text and
    other non-ASCII characters correctly. Multiple differences are joined
    with ``;``. A cell that starts like a formula (``=``, ``-`` ...) gets a
    leading ``'`` so Excel shows it as text (ADR 0040).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_COLUMNS)
        for case in comparison.cases:
            base, head = case.base, case.head
            cells = (
                base.id,
                base.db_id,
                base.difficulty or "",
                case.change,
                status_of(base.verdict),
                status_of(head.verdict),
                ";".join(_outputs(base)),
                ";".join(_outputs(head)),
                base.question,
                base.gold_sql,
                base.pred_sql,
                head.pred_sql,
            )
            writer.writerow(excel_safe(cell) for cell in cells)
