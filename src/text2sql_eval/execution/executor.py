"""Run SQL read-only against SQLite databases, with a per-query deadline.

The deadline is enforced by SQLite's progress handler (ADR 0020); defaults
follow ADR 0021.
"""

from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from text2sql_eval.errors import InputError

DEFAULT_TIMEOUT_SECONDS = 30.0
"""Same value as BIRD's official script, but applied to each query separately."""

# SQLite virtual machine instructions between deadline checks. Small enough to
# stop within milliseconds, large enough that the check costs nothing visible.
_PROGRESS_INTERVAL = 10_000
_FETCH_BATCH = 1_000

SqlValue = int | float | str | bytes | None
"""The Python types sqlite3 returns for SQLite values (no type conversion)."""


@dataclass(frozen=True)
class Rows:
    """A query that finished. ``columns`` are the result column names."""

    columns: tuple[str, ...]
    rows: tuple[tuple[SqlValue, ...], ...]


@dataclass(frozen=True)
class QueryFailure:
    """A query that did not produce rows.

    ``kind`` is ``"error"`` (SQLite rejected or failed the query),
    ``"timeout"`` (the deadline passed) or ``"row_limit"`` (more rows than
    allowed).
    """

    kind: Literal["error", "timeout", "row_limit"]
    message: str


QueryResult = Rows | QueryFailure


@dataclass(frozen=True)
class Query:
    """One SQL statement to run against one database file."""

    db_path: Path
    sql: str


def default_workers() -> int:
    """Number of worker threads used when the caller does not choose."""
    return min(8, os.cpu_count() or 1)


def execute_query(
    db_path: Path,
    sql: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_rows: int | None = None,
) -> QueryResult:
    """Run one statement on a read-only connection and collect its rows.

    Failures of the SQL itself (syntax errors, unknown tables, writes, more
    than one statement, the deadline, the row limit) are returned as
    ``QueryFailure`` rather than raised, because they are results to judge.

    Raises:
        InputError: if ``db_path`` is not an existing file.

    Example:
        >>> result = execute_query(Path("superhero.sqlite"), "SELECT COUNT(*) FROM superhero")
        >>> result
        Rows(columns=('COUNT(*)',), rows=((750,),))
    """
    _require_database(db_path)
    deadline = time.monotonic() + timeout
    timed_out = False

    def stop_after_deadline() -> int:
        nonlocal timed_out
        if time.monotonic() > deadline:
            timed_out = True
            return 1  # a non-zero return makes SQLite abort the statement
        return 0

    # as_uri() percent-encodes the path, so names with spaces or '#' work.
    connection = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.set_progress_handler(stop_after_deadline, _PROGRESS_INTERVAL)
        cursor = connection.execute(sql)
        columns = tuple(str(column[0]) for column in cursor.description or ())
        rows: list[tuple[SqlValue, ...]] = []
        while batch := cursor.fetchmany(_FETCH_BATCH):
            rows.extend(batch)
            if max_rows is not None and len(rows) > max_rows:
                return QueryFailure("row_limit", f"more than {max_rows} rows")
        return Rows(columns=columns, rows=tuple(rows))
    except sqlite3.Error as exc:
        if timed_out:
            return QueryFailure("timeout", f"did not finish within {timeout:g} s")
        return QueryFailure("error", str(exc))
    finally:
        connection.close()


def execute_all(
    queries: Sequence[Query],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_rows: int | None = None,
    workers: int | None = None,
) -> list[QueryResult]:
    """Run many queries in parallel threads; results come back in input order.

    Each query opens its own connection. sqlite3 releases the GIL while a
    statement runs, so threads execute queries truly in parallel.

    Raises:
        InputError: if any database file is missing (checked before running).
        ValueError: if ``workers`` is less than 1.

    Example:
        >>> db = Path("superhero.sqlite")
        >>> execute_all([Query(db, "SELECT 1"), Query(db, "SELEC")], workers=2)
        [Rows(columns=('1',), rows=((1,),)), QueryFailure(kind='error', message=...)]
    """
    if workers is not None and workers < 1:
        raise ValueError(f"workers must be at least 1, got {workers}")
    for db_path in sorted({query.db_path for query in queries}):
        _require_database(db_path)

    def run(query: Query) -> QueryResult:
        return execute_query(
            query.db_path, query.sql, timeout=timeout, max_rows=max_rows
        )

    with ThreadPoolExecutor(max_workers=workers or default_workers()) as pool:
        return list(pool.map(run, queries))


def _require_database(db_path: Path) -> None:
    if not db_path.is_file():
        raise InputError(
            db_path,
            "database file not found",
            hint="databases are expected at <db-dir>/<db_id>/<db_id>.sqlite",
        )
