import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

import pytest

import text2sql_eval
from text2sql_eval.datasets.bird import Case, Dataset, load_bird, load_bird_tied
from text2sql_eval.datasets.predictions import Prediction
from text2sql_eval.errors import InputError
from text2sql_eval.evaluate import evaluate, evaluate_files
from text2sql_eval.execution.executor import DEFAULT_MAX_ROWS, QueryFailure
from text2sql_eval.judge.ex import Correct, ExecError, Incorrect, status_of
from text2sql_eval.runfile import (
    SAMPLE_ROWS,
    FileRef,
    ResultSample,
    RunSettings,
    sha256_of,
)

BIRD_MINI = Path(__file__).resolve().parents[1] / "examples/bird-mini"


def _case(case_id: str, gold_sql: str) -> Case:
    return Case(
        id=case_id,
        db_id="toy",
        question=f"question {case_id}",
        evidence="",
        gold_sql=gold_sql,
        difficulty="simple",
    )


@pytest.fixture
def db_dir(tmp_path: Path) -> Path:
    path = tmp_path / "dbs" / "toy" / "toy.sqlite"
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE t (x INTEGER)")
        connection.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(30)])
    return tmp_path / "dbs"


def test_records_every_kind_of_outcome(db_dir: Path) -> None:
    dataset = Dataset(
        path=Path("toy.json"),
        cases=(
            _case("1", "SELECT COUNT(*) FROM t"),
            _case("2", "SELECT MAX(x) FROM t"),
            _case("3", "SELECT x FROM t WHERE x < 0"),  # gold result is empty
            _case("4", "SELECT nope FROM t"),  # broken gold SQL
            _case("5", "SELECT x FROM t WHERE x < 0"),
            _case("6", "SELECT MAX(x) FROM t"),
        ),
    )
    predictions = {
        "1": Prediction("1", "SELECT COUNT(x) FROM t"),
        "2": Prediction("2", "SELECT MIN(x) FROM t"),
        "3": Prediction("3", ""),
        "4": Prediction("4", "SELECT 1"),
        # "5" is missing
        "6": Prediction("6", ""),
    }

    records = evaluate(dataset, predictions, db_dir=db_dir)

    assert [r.id for r in records] == ["1", "2", "3", "4", "5", "6"]
    assert records[0].verdict == Correct()
    assert records[1].verdict == Incorrect()
    assert isinstance(records[2].verdict, Correct)
    assert [f.kind for f in records[2].verdict.flags] == ["empty_prediction_correct"]
    assert records[2].prediction_state == "empty"
    assert isinstance(records[3].verdict, ExecError)
    assert records[3].verdict.side == "gold"
    assert records[4].prediction_state == "missing"
    assert records[4].pred_sql == ""
    assert [f.kind for f in records[4].verdict.flags] == ["empty_prediction_correct"]
    assert isinstance(records[5].verdict, Incorrect)


def test_wrong_cases_carry_facts_and_correct_ones_do_not(db_dir: Path) -> None:
    dataset = Dataset(
        path=Path("toy.json"),
        cases=(
            _case("1", "SELECT COUNT(*) FROM t"),
            _case("2", "SELECT MAX(x) FROM t WHERE x < 10"),
            _case("3", "SELECT nope FROM t"),
            _case("4", "SELECT MAX(x) FROM t"),
        ),
    )
    predictions = {
        "1": Prediction("1", "SELECT COUNT(x) FROM t"),
        "2": Prediction("2", "SELECT MIN(x) FROM t WHERE x < 20"),
        "3": Prediction("3", "SELECT 1"),
        "4": Prediction("4", ""),
    }

    records = evaluate(dataset, predictions, db_dir=db_dir)

    assert records[0].diff is None  # correct
    diff = records[1].diff
    assert diff is not None
    assert diff.output.differences == ("single_value_differs",)
    assert [(f.kind, f.gold, f.pred) for f in diff.structure.facts] == [
        ("where_value", "x < 10", "x < 20"),
        ("aggregation", "MAX(x)", "MIN(x)"),
    ]
    assert records[2].diff is None  # the gold query failed: not the model's fault
    assert records[3].diff is not None
    assert records[3].diff.output.differences == ("empty_result",)


def test_keeps_only_a_sample_of_long_results(db_dir: Path) -> None:
    dataset = Dataset(path=Path("toy.json"), cases=(_case("1", "SELECT x FROM t"),))

    (record,) = evaluate(
        dataset, {"1": Prediction("1", "SELECT x FROM t")}, db_dir=db_dir
    )

    assert isinstance(record.gold, ResultSample)
    assert record.gold.row_count == 30
    assert len(record.gold.rows) == SAMPLE_ROWS


def test_passes_limits_through_to_the_executor(db_dir: Path) -> None:
    dataset = Dataset(path=Path("toy.json"), cases=(_case("1", "SELECT 1"),))

    (record,) = evaluate(
        dataset, {"1": Prediction("1", "SELECT x FROM t")}, db_dir=db_dir, max_rows=5
    )

    assert record.pred == QueryFailure("row_limit", "more than 5 rows")
    assert isinstance(record.verdict, ExecError)


def test_missing_database_is_an_input_error(tmp_path: Path) -> None:
    dataset = Dataset(path=Path("toy.json"), cases=(_case("1", "SELECT 1"),))

    with pytest.raises(InputError, match="database file not found"):
        evaluate(dataset, {}, db_dir=tmp_path)


def test_gold_as_predictions_scores_100_percent_on_bird_mini() -> None:
    dataset = load_bird(BIRD_MINI / "dev.json")
    tied = load_bird_tied(BIRD_MINI / "dev_tied_append.json", dataset)
    gold_as_pred = {c.id: Prediction(c.id, c.gold_sql) for c in dataset.cases}

    records = evaluate(
        dataset, gold_as_pred, db_dir=BIRD_MINI / "dev_databases", tied=tied
    )

    assert Counter(status_of(r.verdict) for r in records) == {"correct": 432}
    flagged = [r.id for r in records if r.verdict.flags]
    assert sorted(flagged) == sorted(tied)  # only the "tied alternative exists" note


# --- evaluate_files ----------------------------------------------------------


@pytest.fixture
def toy_dataset(tmp_path: Path) -> Path:
    path = tmp_path / "dev.json"
    rows = [
        {
            "question_id": 1,
            "db_id": "toy",
            "question": "How many?",
            "evidence": "",
            "SQL": "SELECT COUNT(*) FROM t",
            "difficulty": "simple",
        },
        {
            "question_id": 2,
            "db_id": "toy",
            "question": "Largest?",
            "evidence": "",
            "SQL": "SELECT MAX(x) FROM t",
            "difficulty": "moderate",
        },
    ]
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_evaluate_files_records_inputs_settings_and_meta(
    tmp_path: Path, db_dir: Path, toy_dataset: Path
) -> None:
    pred = tmp_path / "p.txt"
    pred.write_text("SELECT COUNT(*) FROM t\nSELECT MIN(x) FROM t\n", encoding="utf-8")

    run = evaluate_files(
        toy_dataset, pred, db_dir=db_dir, timeout=5.0, meta={"model": "m"}
    )

    assert [status_of(case.verdict) for case in run.cases] == ["correct", "incorrect"]
    assert run.prediction_format == "text"
    assert run.dataset == FileRef(str(toy_dataset), sha256_of(toy_dataset))
    assert run.predictions == FileRef(str(pred), sha256_of(pred))
    assert run.tied is None
    assert run.db_dir == str(db_dir)
    assert run.settings == RunSettings(
        timeout_seconds=5.0, max_rows=DEFAULT_MAX_ROWS, allow_missing=False
    )
    assert run.meta == {"model": "m"}
    assert run.tool_version == text2sql_eval.__version__
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", run.created_at)


def test_evaluate_files_reads_jsonl_and_can_allow_missing_cases(
    tmp_path: Path, db_dir: Path, toy_dataset: Path
) -> None:
    pred = tmp_path / "p.jsonl"
    pred.write_text('{"id": 1, "sql": "SELECT COUNT(*) FROM t"}\n', encoding="utf-8")

    run = evaluate_files(toy_dataset, pred, db_dir=db_dir, allow_missing=True)

    assert run.prediction_format == "jsonl"
    assert [case.prediction_state for case in run.cases] == ["given", "missing"]
    assert run.settings.allow_missing


def test_prediction_format_overrides_the_extension(
    tmp_path: Path, db_dir: Path, toy_dataset: Path
) -> None:
    pred = tmp_path / "p.sql"
    pred.write_text("SELECT 1\nSELECT 2\n", encoding="utf-8")

    run = evaluate_files(toy_dataset, pred, db_dir=db_dir, prediction_format="text")

    assert run.prediction_format == "text"


@pytest.mark.parametrize(
    ("name", "allow_missing", "problem"),
    [
        ("p.csv", False, "cannot tell the prediction format from the extension"),
        ("p.txt", True, "--allow-missing only applies to JSONL predictions"),
    ],
)
def test_evaluate_files_rejects_unusable_prediction_options(
    tmp_path: Path,
    db_dir: Path,
    toy_dataset: Path,
    name: str,
    allow_missing: bool,
    problem: str,
) -> None:
    pred = tmp_path / name
    pred.write_text("SELECT 1\nSELECT 2\n", encoding="utf-8")

    with pytest.raises(InputError, match=problem):
        evaluate_files(toy_dataset, pred, db_dir=db_dir, allow_missing=allow_missing)
