import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from text2sql_eval.datasets.bird import Case, Dataset, load_bird, load_bird_tied
from text2sql_eval.datasets.predictions import Prediction
from text2sql_eval.errors import InputError
from text2sql_eval.evaluate import evaluate
from text2sql_eval.execution.executor import QueryFailure
from text2sql_eval.judge.ex import Correct, ExecError, Incorrect, status_of
from text2sql_eval.runfile import SAMPLE_ROWS, ResultSample

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
        ),
    )
    predictions = {
        "1": Prediction("1", "SELECT COUNT(x) FROM t"),
        "2": Prediction("2", "SELECT MIN(x) FROM t"),
        "3": Prediction("3", ""),
        "4": Prediction("4", "SELECT 1"),
        # "5" is missing
    }

    records = evaluate(dataset, predictions, db_dir=db_dir)

    assert [r.id for r in records] == ["1", "2", "3", "4", "5"]
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
