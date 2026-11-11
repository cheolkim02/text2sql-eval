"""The run file: one JSON document per evaluation run (ADR 0026).

``report`` and ``compare`` read it, and people open it directly, so the format
is documented in ``docs/reference/run-file.md`` and versioned by
``SCHEMA_VERSION``.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeVar, get_args

from text2sql_eval.datasets._json import as_array, as_object, parse_json, read_utf8
from text2sql_eval.errors import InputError
from text2sql_eval.execution.executor import QueryFailure, Rows, SqlValue
from text2sql_eval.facts import CaseDiff
from text2sql_eval.facts.output import OutputDiff, OutputDifference, Relation
from text2sql_eval.facts.structure import Fact, FactKind, StructureReport
from text2sql_eval.judge.ex import (
    Correct,
    ExecError,
    Flag,
    FlagKind,
    Incorrect,
    Verdict,
    status_of,
)

SCHEMA_VERSION = 3
SAMPLE_ROWS = 20
"""Rows kept per query result; ``row_count`` still says how many there were."""

# A bound TypeVar instead of 3.12's ``def f[T: str]`` (ADR 0009).
_Choice = TypeVar("_Choice", bound=str)

Side = Literal["gold", "pred"]

PredictionState = Literal["given", "empty", "missing"]
PredictionFormat = Literal["text", "jsonl"]


@dataclass(frozen=True)
class FileRef:
    """An input file as it was when the run started."""

    path: str
    sha256: str


@dataclass(frozen=True)
class ResultSample:
    """The first ``SAMPLE_ROWS`` rows of a query result, and the full count."""

    columns: tuple[str, ...]
    rows: tuple[tuple[SqlValue, ...], ...]
    row_count: int


QuerySummary = ResultSample | QueryFailure


@dataclass(frozen=True)
class CaseRecord:
    """Everything needed to show and compare one judged case."""

    id: str
    db_id: str
    difficulty: str | None
    question: str
    evidence: str
    gold_sql: str
    pred_sql: str
    prediction_state: PredictionState
    verdict: Verdict
    gold: QuerySummary
    pred: QuerySummary
    pred_meta: dict[str, object] = field(default_factory=dict[str, object])
    diff: CaseDiff | None = None
    """Why the case is not correct; ``None`` for correct cases (ADR 0031)."""


@dataclass(frozen=True)
class RunSettings:
    timeout_seconds: float
    max_rows: int | None
    allow_missing: bool


@dataclass(frozen=True)
class Summary:
    total: int
    correct: int
    incorrect: int
    error: int

    @property
    def ex(self) -> float:
        """Execution accuracy: correct cases over all cases (0.0 for no cases)."""
        return self.correct / self.total if self.total else 0.0


@dataclass(frozen=True)
class Run:
    """One evaluation run: inputs, settings, user metadata and judged cases."""

    tool_version: str
    created_at: str
    dataset: FileRef
    predictions: FileRef
    prediction_format: PredictionFormat
    tied: FileRef | None
    db_dir: str
    settings: RunSettings
    meta: dict[str, str]
    cases: tuple[CaseRecord, ...]

    @property
    def summary(self) -> Summary:
        counts = Counter(status_of(case.verdict) for case in self.cases)
        return Summary(
            total=len(self.cases),
            correct=counts["correct"],
            incorrect=counts["incorrect"],
            error=counts["error"],
        )


def sha256_of(path: Path) -> str:
    """Hex SHA-256 of a file, so a later run can tell whether inputs changed."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def sample_of(result: Rows | QueryFailure) -> QuerySummary:
    """Keep the first ``SAMPLE_ROWS`` rows of a result for the run file."""
    if isinstance(result, QueryFailure):
        return result
    return ResultSample(
        columns=result.columns,
        rows=result.rows[:SAMPLE_ROWS],
        row_count=len(result.rows),
    )


# --- writing ---------------------------------------------------------------


def write_run(run: Run, path: Path) -> None:
    """Write ``run`` as UTF-8 JSON, creating parent directories as needed."""
    summary = run.summary
    document: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "text2sql-eval", "version": run.tool_version},
        "created_at": run.created_at,
        "inputs": {
            "dataset": _file_ref(run.dataset),
            "predictions": {
                **_file_ref(run.predictions),
                "format": run.prediction_format,
            },
            "tied": None if run.tied is None else _file_ref(run.tied),
            "db_dir": run.db_dir,
        },
        "settings": {
            "timeout_seconds": run.settings.timeout_seconds,
            "max_rows": run.settings.max_rows,
            "allow_missing": run.settings.allow_missing,
        },
        "meta": run.meta,
        "summary": {
            "total": summary.total,
            "correct": summary.correct,
            "incorrect": summary.incorrect,
            "error": summary.error,
            "ex": summary.ex,
        },
        "cases": [_case_to_json(case) for case in run.cases],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    # allow_nan=False: NaN and Infinity are not JSON; _encode_value spells them out.
    text = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")


def _file_ref(ref: FileRef) -> dict[str, object]:
    return {"path": ref.path, "sha256": ref.sha256}


def _case_to_json(case: CaseRecord) -> dict[str, object]:
    verdict = case.verdict
    error = (
        {"side": verdict.side, "kind": verdict.kind, "message": verdict.message}
        if isinstance(verdict, ExecError)
        else None
    )
    return {
        "id": case.id,
        "db_id": case.db_id,
        "difficulty": case.difficulty,
        "question": case.question,
        "evidence": case.evidence,
        "gold_sql": case.gold_sql,
        "pred_sql": case.pred_sql,
        "prediction_state": case.prediction_state,
        "pred_meta": case.pred_meta,
        "status": status_of(verdict),
        "error": error,
        "flags": [{"kind": flag.kind, "detail": flag.detail} for flag in verdict.flags],
        "gold": _summary_to_json(case.gold),
        "pred": _summary_to_json(case.pred),
        "diff": None if case.diff is None else _diff_to_json(case.diff),
    }


def _diff_to_json(diff: CaseDiff) -> dict[str, object]:
    output, structure = diff.output, diff.structure
    return {
        "output": {
            "differences": list(output.differences),
            "gold_columns": output.gold_columns,
            "pred_columns": output.pred_columns,
            "gold_distinct_rows": output.gold_distinct_rows,
            "pred_distinct_rows": output.pred_distinct_rows,
            "gold_contained": output.gold_contained,
            "relation": output.relation,
        },
        "sql_structure": {
            "differences": [
                {"kind": fact.kind, "gold": fact.gold, "pred": fact.pred}
                for fact in structure.facts
            ],
            "parse_failed": structure.parse_failed,
        },
    }


def _summary_to_json(summary: QuerySummary) -> dict[str, object]:
    if isinstance(summary, QueryFailure):
        return {"failure": {"kind": summary.kind, "message": summary.message}}
    return {
        "columns": list(summary.columns),
        "rows": [[_encode_value(value) for value in row] for row in summary.rows],
        "row_count": summary.row_count,
    }


def _encode_value(value: SqlValue) -> object:
    """Map a SQLite value to JSON. Bytes and non-finite floats get tagged objects."""
    if isinstance(value, bytes):
        return {"$bytes": value.hex()}
    if isinstance(value, float) and not math.isfinite(value):
        return {"$float": repr(value)}  # 'inf', '-inf' or 'nan'
    return value


# --- reading ---------------------------------------------------------------


def read_run(path: Path) -> Run:
    """Read a run file written by ``write_run``.

    Raises:
        InputError: if the file is unreadable, has another ``schema_version``,
            or is missing fields or has fields of the wrong type.
    """
    reader = _Reader(path)
    root = reader.obj(parse_json(read_utf8(path), path), "the file")
    version = root.get("schema_version")
    if version != SCHEMA_VERSION:
        raise InputError(
            path,
            f"schema_version is {version!r}, but this tool reads {SCHEMA_VERSION}",
            hint="re-run eval with this version of text2sql-eval",
        )
    tool = reader.obj(root.get("tool"), "tool")
    inputs = reader.obj(root.get("inputs"), "inputs")
    predictions = reader.obj(inputs.get("predictions"), "inputs.predictions")
    prediction_format = reader.choice(
        predictions.get("format"),
        "inputs.predictions.format",
        get_args(PredictionFormat),
    )
    tied_value = inputs.get("tied")
    settings = reader.obj(root.get("settings"), "settings")
    meta = reader.obj(root.get("meta"), "meta")
    cases = reader.array(root.get("cases"), "cases")
    return Run(
        tool_version=reader.str_(tool.get("version"), "tool.version"),
        created_at=reader.str_(root.get("created_at"), "created_at"),
        dataset=reader.file_ref(inputs.get("dataset"), "inputs.dataset"),
        predictions=reader.file_ref(predictions, "inputs.predictions"),
        prediction_format=prediction_format,
        tied=None if tied_value is None else reader.file_ref(tied_value, "inputs.tied"),
        db_dir=reader.str_(inputs.get("db_dir"), "inputs.db_dir"),
        settings=RunSettings(
            timeout_seconds=reader.number(
                settings.get("timeout_seconds"), "settings.timeout_seconds"
            ),
            max_rows=reader.optional_int(settings.get("max_rows"), "settings.max_rows"),
            allow_missing=reader.bool_(
                settings.get("allow_missing"), "settings.allow_missing"
            ),
        ),
        meta={key: reader.str_(value, f"meta.{key}") for key, value in meta.items()},
        cases=tuple(
            reader.case(value, f"cases[{index}]") for index, value in enumerate(cases)
        ),
    )


class _Reader:
    """Typed field access that reports the JSON path of anything malformed."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def fail(self, where: str, expected: str) -> InputError:
        return InputError(
            self.path,
            f"{where} must be {expected}",
            hint="the file may be damaged or not written by text2sql-eval",
        )

    def obj(self, value: object, where: str) -> dict[str, object]:
        result = as_object(value)
        if result is None:
            raise self.fail(where, "an object")
        return result

    def array(self, value: object, where: str) -> list[object]:
        result = as_array(value)
        if result is None:
            raise self.fail(where, "an array")
        return result

    def str_(self, value: object, where: str) -> str:
        if not isinstance(value, str):
            raise self.fail(where, "a string")
        return value

    def optional_str(self, value: object, where: str) -> str | None:
        return None if value is None else self.str_(value, where)

    def int_(self, value: object, where: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise self.fail(where, "an integer")
        return value

    def optional_int(self, value: object, where: str) -> int | None:
        return None if value is None else self.int_(value, where)

    def number(self, value: object, where: str) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise self.fail(where, "a number")
        return float(value)

    def bool_(self, value: object, where: str) -> bool:
        if not isinstance(value, bool):
            raise self.fail(where, "true or false")
        return value

    def choice(
        self, value: object, where: str, options: tuple[_Choice, ...]
    ) -> _Choice:
        for option in options:
            if value == option:
                return option
        raise self.fail(where, "one of " + ", ".join(options))

    def file_ref(self, value: object, where: str) -> FileRef:
        obj = self.obj(value, where)
        return FileRef(
            path=self.str_(obj.get("path"), f"{where}.path"),
            sha256=self.str_(obj.get("sha256"), f"{where}.sha256"),
        )

    def case(self, value: object, where: str) -> CaseRecord:
        obj = self.obj(value, where)
        flags = tuple(
            self.flag(item, f"{where}.flags[{index}]")
            for index, item in enumerate(self.array(obj.get("flags"), f"{where}.flags"))
        )
        return CaseRecord(
            id=self.str_(obj.get("id"), f"{where}.id"),
            db_id=self.str_(obj.get("db_id"), f"{where}.db_id"),
            difficulty=self.optional_str(obj.get("difficulty"), f"{where}.difficulty"),
            question=self.str_(obj.get("question"), f"{where}.question"),
            evidence=self.str_(obj.get("evidence"), f"{where}.evidence"),
            gold_sql=self.str_(obj.get("gold_sql"), f"{where}.gold_sql"),
            pred_sql=self.str_(obj.get("pred_sql"), f"{where}.pred_sql"),
            prediction_state=self.choice(
                obj.get("prediction_state"),
                f"{where}.prediction_state",
                get_args(PredictionState),
            ),
            verdict=self.verdict(obj, where, flags),
            gold=self.summary(obj.get("gold"), f"{where}.gold"),
            pred=self.summary(obj.get("pred"), f"{where}.pred"),
            pred_meta=self.obj(obj.get("pred_meta"), f"{where}.pred_meta"),
            diff=self.diff(obj.get("diff"), f"{where}.diff"),
        )

    def diff(self, value: object, where: str) -> CaseDiff | None:
        if value is None:
            return None
        obj = self.obj(value, where)
        out_where, sql_where = f"{where}.output", f"{where}.sql_structure"
        output = self.obj(obj.get("output"), out_where)
        structure = self.obj(obj.get("sql_structure"), sql_where)
        relation: Relation | None = None
        if (relation_value := output.get("relation")) is not None:
            relation = self.choice(
                relation_value, f"{out_where}.relation", get_args(Relation)
            )
        contained: bool | None = None
        if (contained_value := output.get("gold_contained")) is not None:
            contained = self.bool_(contained_value, f"{out_where}.gold_contained")
        parse_failed: Side | None = None
        if (parse_failed_value := structure.get("parse_failed")) is not None:
            parse_failed = self.choice(
                parse_failed_value, f"{sql_where}.parse_failed", get_args(Side)
            )
        differences = self.array(output.get("differences"), f"{out_where}.differences")
        facts = self.array(structure.get("differences"), f"{sql_where}.differences")
        return CaseDiff(
            output=OutputDiff(
                differences=tuple(
                    self.choice(
                        item,
                        f"{out_where}.differences[{index}]",
                        get_args(OutputDifference),
                    )
                    for index, item in enumerate(differences)
                ),
                gold_columns=self.int_(
                    output.get("gold_columns"), f"{out_where}.gold_columns"
                ),
                pred_columns=self.int_(
                    output.get("pred_columns"), f"{out_where}.pred_columns"
                ),
                gold_distinct_rows=self.int_(
                    output.get("gold_distinct_rows"), f"{out_where}.gold_distinct_rows"
                ),
                pred_distinct_rows=self.int_(
                    output.get("pred_distinct_rows"), f"{out_where}.pred_distinct_rows"
                ),
                gold_contained=contained,
                relation=relation,
            ),
            structure=StructureReport(
                facts=tuple(
                    self.fact(item, f"{sql_where}.differences[{index}]")
                    for index, item in enumerate(facts)
                ),
                parse_failed=parse_failed,
            ),
        )

    def fact(self, value: object, where: str) -> Fact:
        obj = self.obj(value, where)
        kind: FactKind = self.choice(
            obj.get("kind"), f"{where}.kind", get_args(FactKind)
        )
        return Fact(
            kind=kind,
            gold=self.str_(obj.get("gold"), f"{where}.gold"),
            pred=self.str_(obj.get("pred"), f"{where}.pred"),
        )

    def flag(self, value: object, where: str) -> Flag:
        obj = self.obj(value, where)
        kind: FlagKind = self.choice(
            obj.get("kind"), f"{where}.kind", get_args(FlagKind)
        )
        return Flag(kind=kind, detail=self.str_(obj.get("detail"), f"{where}.detail"))

    def verdict(
        self, obj: dict[str, object], where: str, flags: tuple[Flag, ...]
    ) -> Verdict:
        status = self.choice(
            obj.get("status"), f"{where}.status", ("correct", "incorrect", "error")
        )
        if status == "correct":
            return Correct(flags=flags)
        if status == "incorrect":
            return Incorrect(flags=flags)
        error = self.obj(obj.get("error"), f"{where}.error")
        return ExecError(
            side=self.choice(
                error.get("side"), f"{where}.error.side", ("pred", "gold")
            ),
            kind=self.choice(
                error.get("kind"),
                f"{where}.error.kind",
                ("error", "timeout", "row_limit"),
            ),
            message=self.str_(error.get("message"), f"{where}.error.message"),
            flags=flags,
        )

    def summary(self, value: object, where: str) -> QuerySummary:
        obj = self.obj(value, where)
        if "failure" in obj:
            failure = self.obj(obj["failure"], f"{where}.failure")
            return QueryFailure(
                kind=self.choice(
                    failure.get("kind"),
                    f"{where}.failure.kind",
                    ("error", "timeout", "row_limit"),
                ),
                message=self.str_(failure.get("message"), f"{where}.failure.message"),
            )
        rows = self.array(obj.get("rows"), f"{where}.rows")
        return ResultSample(
            columns=tuple(
                self.str_(column, f"{where}.columns")
                for column in self.array(obj.get("columns"), f"{where}.columns")
            ),
            rows=tuple(
                tuple(
                    self.value(item, f"{where}.rows[{index}]")
                    for item in self.array(row, f"{where}.rows[{index}]")
                )
                for index, row in enumerate(rows)
            ),
            row_count=self.int_(obj.get("row_count"), f"{where}.row_count"),
        )

    def value(self, value: object, where: str) -> SqlValue:
        if (
            value is None
            or isinstance(value, str | int | float)
            and not isinstance(value, bool)
        ):
            return value
        tagged = self.obj(value, where)
        if "$bytes" in tagged:
            return bytes.fromhex(self.str_(tagged["$bytes"], f"{where}.$bytes"))
        if "$float" in tagged:
            return float(self.str_(tagged["$float"], f"{where}.$float"))
        raise self.fail(where, "a SQL value")
