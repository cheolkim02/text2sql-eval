"""Helpers shared by several test files."""

import subprocess
import sys
from pathlib import Path

from text2sql_eval import CaseRecord, FileRef, Run, RunSettings


def run_cli(*args: str | Path) -> subprocess.CompletedProcess[str]:
    """Run ``text2sql-eval`` as a real process and capture its output."""
    return subprocess.run(
        [sys.executable, "-m", "text2sql_eval.cli.main", *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def make_run(
    *cases: CaseRecord,
    dataset_hash: str = "a" * 64,
    tied: FileRef | None = None,
    allow_missing: bool = False,
    meta: dict[str, str] | None = None,
) -> Run:
    """A run of ``cases`` with fixed, made-up inputs and settings."""
    return Run(
        tool_version="0.1.0",
        created_at="2026-11-11T00:00:00Z",
        dataset=FileRef("dev.json", dataset_hash),
        predictions=FileRef("p.jsonl", "b" * 64),
        prediction_format="jsonl",
        tied=tied,
        db_dir="dbs",
        settings=RunSettings(
            timeout_seconds=30.0, max_rows=None, allow_missing=allow_missing
        ),
        meta=meta or {},
        cases=cases,
    )
