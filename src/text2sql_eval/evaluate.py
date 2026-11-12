"""Execute and judge every case of a dataset against a set of predictions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from text2sql_eval.datasets.bird import Case, Dataset, load_bird, load_bird_tied
from text2sql_eval.datasets.predictions import (
    Prediction,
    load_jsonl_predictions,
    load_text_predictions,
)
from text2sql_eval.errors import InputError
from text2sql_eval.execution.executor import (
    DEFAULT_TIMEOUT_SECONDS,
    Query,
    QueryResult,
    execute_all,
)
from text2sql_eval.facts import CaseDiff
from text2sql_eval.facts.output import compare_outputs
from text2sql_eval.facts.structure import structural_facts
from text2sql_eval.judge.ex import Correct, ExecError, Verdict, judge_case
from text2sql_eval.runfile import (
    CaseRecord,
    FileRef,
    PredictionFormat,
    PredictionState,
    Run,
    RunSettings,
    sample_of,
    sha256_of,
)

_FORMAT_BY_SUFFIX: dict[str, PredictionFormat] = {".txt": "text", ".jsonl": "jsonl"}


@dataclass(frozen=True)
class _Plan:
    """Where each case's queries sit in the flat list sent to ``execute_all``."""

    case: Case
    prediction: Prediction | None
    gold_index: int
    pred_index: int
    tied_index: int | None


def evaluate_files(
    dataset: Path,
    predictions: Path,
    *,
    db_dir: Path,
    prediction_format: PredictionFormat | None = None,
    allow_missing: bool = False,
    tied: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_rows: int | None = None,
    workers: int | None = None,
    meta: Mapping[str, str] | None = None,
) -> Run:
    """Do what ``text2sql-eval eval`` does and return the run.

    Reads the dataset and the predictions, executes and judges every case,
    and records the inputs (with SHA-256 hashes), the settings and ``meta``.
    Write the result with :func:`write_run`.

    Args:
        dataset: BIRD question file.
        predictions: Predictions, one SQL per line (``.txt``) or JSONL.
        db_dir: Folder with ``<db_id>/<db_id>.sqlite`` databases.
        prediction_format: ``"text"`` or ``"jsonl"``; ``None`` reads it from
            the file extension (ADR 0027).
        allow_missing: JSONL only: judge cases without a line as empty
            predictions instead of failing.
        tied: BIRD's tied-rows alternative gold file, used only for flags.
        timeout: Seconds allowed per query.
        max_rows: Row limit per query, or ``None`` for no limit.
        workers: Worker threads, or ``None`` for the default.
        meta: Facts about the run to record, such as the model name.

    Raises:
        InputError: if an input file is malformed, does not match the
            dataset, or a database file is missing.

    Example:
        >>> run = evaluate_files(
        ...     Path("examples/bird-mini/dev.json"),
        ...     Path("examples/results/gpt-4o-mini-evidence.jsonl"),
        ...     db_dir=Path("examples/bird-mini/dev_databases"),
        ...     meta={"model": "gpt-4o-mini"},
        ... )
        >>> round(run.summary.ex, 4)
        0.6181
    """
    pred_format = prediction_format or _format_from_extension(predictions)
    if allow_missing and pred_format != "jsonl":
        raise InputError(
            predictions,
            "--allow-missing only applies to JSONL predictions",
            hint="text predictions need one line per case; leave a line empty instead",
        )
    loaded = load_bird(dataset)
    if pred_format == "text":
        by_id = load_text_predictions(predictions, loaded)
    else:
        by_id = load_jsonl_predictions(predictions, loaded, allow_missing=allow_missing)
    tied_sql = None if tied is None else load_bird_tied(tied, loaded)
    records = evaluate(
        loaded,
        by_id,
        db_dir=db_dir,
        tied=tied_sql,
        timeout=timeout,
        max_rows=max_rows,
        workers=workers,
    )
    return Run(
        tool_version=version("text2sql-eval"),
        created_at=datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        dataset=FileRef(str(dataset), sha256_of(dataset)),
        predictions=FileRef(str(predictions), sha256_of(predictions)),
        prediction_format=pred_format,
        tied=None if tied is None else FileRef(str(tied), sha256_of(tied)),
        db_dir=str(db_dir),
        settings=RunSettings(
            timeout_seconds=timeout, max_rows=max_rows, allow_missing=allow_missing
        ),
        meta=dict(meta or {}),
        cases=records,
    )


def _format_from_extension(path: Path) -> PredictionFormat:
    detected = _FORMAT_BY_SUFFIX.get(path.suffix.lower())
    if detected is None:
        raise InputError(
            path,
            f"cannot tell the prediction format from the extension '{path.suffix}'",
            hint="use a .txt or .jsonl file, or pass --pred-format text|jsonl",
        )
    return detected


def database_path(db_dir: Path, db_id: str) -> Path:
    """BIRD's layout: ``<db_dir>/<db_id>/<db_id>.sqlite``."""
    return db_dir / db_id / f"{db_id}.sqlite"


def evaluate(
    dataset: Dataset,
    predictions: Mapping[str, Prediction],
    *,
    db_dir: Path,
    tied: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_rows: int | None = None,
    workers: int | None = None,
) -> tuple[CaseRecord, ...]:
    """Run gold, predicted and tied-alternative SQL for every case and judge it.

    A case with no entry in ``predictions`` is judged as an empty prediction
    and recorded as ``"missing"`` (ADR 0023, ADR 0027). All queries go to one
    thread pool, so slow cases do not hold up the rest.

    Args:
        dataset: The cases, in the order the records are returned.
        predictions: Predicted SQL by case id.
        db_dir: Folder with ``<db_id>/<db_id>.sqlite`` databases.
        tied: Tied-rows alternative gold SQL by case id, used only for flags.
        timeout: Seconds allowed per query.
        max_rows: Row limit per query, or ``None`` for no limit.
        workers: Worker threads, or ``None`` for the default.

    Raises:
        InputError: if a database file is missing.

    Example:
        Using the gold SQL as predictions judges every case correct:

        >>> gold_as_pred = {c.id: Prediction(c.id, c.gold_sql) for c in dataset.cases}
        >>> records = evaluate(dataset, gold_as_pred, db_dir=Path("dev_databases"))
        >>> {status_of(record.verdict) for record in records}
        {'correct'}
    """
    tied = tied or {}
    queries: list[Query] = []
    plans: list[_Plan] = []

    def add(case: Case, sql: str) -> int:
        queries.append(Query(database_path(db_dir, case.db_id), sql))
        return len(queries) - 1

    for case in dataset.cases:
        prediction = predictions.get(case.id)
        tied_sql = tied.get(case.id)
        plans.append(
            _Plan(
                case=case,
                prediction=prediction,
                gold_index=add(case, case.gold_sql),
                pred_index=add(case, "" if prediction is None else prediction.sql),
                tied_index=None if tied_sql is None else add(case, tied_sql),
            )
        )

    results = execute_all(queries, timeout=timeout, max_rows=max_rows, workers=workers)
    return tuple(_record(plan, results) for plan in plans)


def _record(plan: _Plan, results: list[QueryResult]) -> CaseRecord:
    case, prediction = plan.case, plan.prediction
    gold = results[plan.gold_index]
    pred = results[plan.pred_index]
    tied = None if plan.tied_index is None else results[plan.tied_index]
    state: PredictionState
    if prediction is None:
        state = "missing"
    elif prediction.sql == "":
        state = "empty"
    else:
        state = "given"
    pred_sql = "" if prediction is None else prediction.sql
    verdict = judge_case(gold, pred, pred_is_empty=state != "given", tied=tied)
    return CaseRecord(
        id=case.id,
        db_id=case.db_id,
        difficulty=case.difficulty,
        question=case.question,
        evidence=case.evidence,
        gold_sql=case.gold_sql,
        pred_sql=pred_sql,
        prediction_state=state,
        verdict=verdict,
        gold=sample_of(gold),
        pred=sample_of(pred),
        pred_meta={} if prediction is None else prediction.meta,
        diff=_diff(verdict, gold, pred, case.gold_sql, pred_sql),
    )


def _diff(
    verdict: Verdict,
    gold: QueryResult,
    pred: QueryResult,
    gold_sql: str,
    pred_sql: str,
) -> CaseDiff | None:
    """Facts for cases the model got wrong (ADR 0031).

    None for correct cases, and for a gold query that failed: that is the
    dataset's problem, not the prediction's.
    """
    if isinstance(verdict, Correct):
        return None
    if isinstance(verdict, ExecError) and verdict.side == "gold":
        return None
    return CaseDiff(
        output=compare_outputs(gold, pred),
        structure=structural_facts(gold_sql, pred_sql),
    )
