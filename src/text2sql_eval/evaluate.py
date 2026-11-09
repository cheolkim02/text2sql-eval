"""Execute and judge every case of a dataset against a set of predictions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from text2sql_eval.datasets.bird import Case, Dataset
from text2sql_eval.datasets.predictions import Prediction
from text2sql_eval.execution.executor import (
    DEFAULT_TIMEOUT_SECONDS,
    Query,
    QueryResult,
    execute_all,
)
from text2sql_eval.judge.ex import judge_case
from text2sql_eval.runfile import CaseRecord, PredictionState, sample_of


@dataclass(frozen=True)
class _Plan:
    """Where each case's queries sit in the flat list sent to ``execute_all``."""

    case: Case
    prediction: Prediction | None
    gold_index: int
    pred_index: int
    tied_index: int | None


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
    return CaseRecord(
        id=case.id,
        db_id=case.db_id,
        difficulty=case.difficulty,
        question=case.question,
        evidence=case.evidence,
        gold_sql=case.gold_sql,
        pred_sql="" if prediction is None else prediction.sql,
        prediction_state=state,
        verdict=judge_case(gold, pred, pred_is_empty=state != "given", tied=tied),
        gold=sample_of(gold),
        pred=sample_of(pred),
        pred_meta={} if prediction is None else prediction.meta,
    )
