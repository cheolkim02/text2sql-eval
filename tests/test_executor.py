import sqlite3
import time
from pathlib import Path

import pytest

from text2sql_eval.datasets.bird import load_bird
from text2sql_eval.errors import InputError
from text2sql_eval.execution.executor import (
    Query,
    QueryFailure,
    Rows,
    execute_all,
    execute_query,
)

# Never finishes: counts upward forever.
ENDLESS_SQL = (
    "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) "
    "SELECT COUNT(*) FROM n"
)


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "toy.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE hero (id INTEGER, name TEXT, height REAL)")
        connection.executemany(
            "INSERT INTO hero VALUES (?, ?, ?)",
            [(1, "Ana", 1.7), (2, "Bo", None), (3, "Cy", 1.9)],
        )
    return path


def test_returns_columns_and_rows_in_order(db: Path) -> None:
    result = execute_query(db, "SELECT id, name AS hero FROM hero ORDER BY id")

    assert result == Rows(
        columns=("id", "hero"),
        rows=((1, "Ana"), (2, "Bo"), (3, "Cy")),
    )


def test_keeps_sqlite_value_types(db: Path) -> None:
    result = execute_query(db, "SELECT height, NULL, x'00ff' FROM hero WHERE id = 2")

    assert result == Rows(
        columns=("height", "NULL", "x'00ff'"),
        rows=((None, None, b"\x00\xff"),),
    )


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("SELEC id FROM hero", "syntax error"),
        ("SELECT nope FROM hero", "no such column: nope"),
        ("SELECT 1; SELECT 2", "one statement at a time"),
        ("DELETE FROM hero", "readonly database"),
    ],
)
def test_reports_sql_failures_as_error_results(
    db: Path, sql: str, message: str
) -> None:
    result = execute_query(db, sql)

    assert isinstance(result, QueryFailure)
    assert result.kind == "error"
    assert message in result.message


def test_write_attempt_leaves_the_database_unchanged(db: Path) -> None:
    execute_query(db, "DELETE FROM hero")

    assert execute_query(db, "SELECT COUNT(*) FROM hero") == Rows(
        columns=("COUNT(*)",), rows=((3,),)
    )


def test_empty_sql_runs_and_returns_no_rows(db: Path) -> None:
    # Same as BIRD's official script; how to judge it is decided by D16.
    assert execute_query(db, "  ") == Rows(columns=(), rows=())


def test_stops_a_query_at_the_deadline(db: Path) -> None:
    started = time.monotonic()

    result = execute_query(db, ENDLESS_SQL, timeout=0.2)

    elapsed = time.monotonic() - started
    assert result == QueryFailure("timeout", "did not finish within 0.2 s")
    assert elapsed < 5  # generous bound: only checks that it did stop


@pytest.mark.parametrize(("max_rows", "expected_kind"), [(2, "row_limit"), (3, None)])
def test_enforces_the_row_limit(
    db: Path, max_rows: int, expected_kind: str | None
) -> None:
    result = execute_query(db, "SELECT id FROM hero", max_rows=max_rows)

    if expected_kind is None:
        assert isinstance(result, Rows)
        assert len(result.rows) == 3
    else:
        assert result == QueryFailure("row_limit", f"more than {max_rows} rows")


def test_handles_paths_with_spaces_and_hash_signs(tmp_path: Path) -> None:
    path = tmp_path / "my dbs #1" / "toy.sqlite"
    path.parent.mkdir()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE t (x INTEGER)")

    assert execute_query(path, "SELECT COUNT(*) FROM t") == Rows(
        columns=("COUNT(*)",), rows=((0,),)
    )


def test_missing_database_is_an_input_error(tmp_path: Path) -> None:
    with pytest.raises(InputError) as excinfo:
        execute_query(tmp_path / "nope" / "nope.sqlite", "SELECT 1")

    assert "<db-dir>/<db_id>/<db_id>.sqlite" in str(excinfo.value)


def test_execute_all_keeps_input_order_and_isolates_failures(db: Path) -> None:
    queries = [Query(db, f"SELECT name FROM hero WHERE id = {i}") for i in (3, 1, 2)]
    queries.insert(1, Query(db, ENDLESS_SQL))
    queries.insert(3, Query(db, "SELEC"))

    results = execute_all(queries, timeout=0.2, workers=4)

    assert [type(result).__name__ for result in results] == [
        "Rows",
        "QueryFailure",
        "Rows",
        "QueryFailure",
        "Rows",
    ]
    assert results[0] == Rows(columns=("name",), rows=(("Cy",),))
    assert results[2] == Rows(columns=("name",), rows=(("Ana",),))
    assert results[4] == Rows(columns=("name",), rows=(("Bo",),))
    assert isinstance(results[1], QueryFailure)
    assert results[1].kind == "timeout"


def test_execute_all_checks_every_database_before_running(
    db: Path, tmp_path: Path
) -> None:
    queries = [Query(db, "SELECT 1"), Query(tmp_path / "missing.sqlite", "SELECT 1")]

    with pytest.raises(InputError, match="database file not found"):
        execute_all(queries)


def test_execute_all_rejects_zero_workers(db: Path) -> None:
    with pytest.raises(ValueError, match="workers must be at least 1"):
        execute_all([Query(db, "SELECT 1")], workers=0)


def test_runs_every_gold_query_in_the_committed_subset() -> None:
    # The bird-mini SOURCE.md claims all gold SQL runs; keep that true.
    root = Path(__file__).resolve().parents[1] / "examples/bird-mini"
    dataset = load_bird(root / "dev.json")
    queries = [
        Query(root / "dev_databases" / c.db_id / f"{c.db_id}.sqlite", c.gold_sql)
        for c in dataset.cases
    ]

    results = execute_all(queries)

    failures = [
        (case.id, result)
        for case, result in zip(dataset.cases, results, strict=True)
        if isinstance(result, QueryFailure)
    ]
    assert failures == []
