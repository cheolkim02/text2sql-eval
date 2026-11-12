"""Deterministic, evidence-backed error analysis for text-to-SQL experiments.

The public API is exactly what ``__all__`` lists (ADR 0043). Anything else,
including the submodules, may change without notice.

Example:
    The same steps as ``text2sql-eval eval`` and ``text2sql-eval report``:

    >>> from pathlib import Path
    >>> import text2sql_eval as t2s
    >>> run = t2s.evaluate_files(
    ...     Path("dev.json"), Path("predictions.jsonl"), db_dir=Path("dev_databases")
    ... )
    >>> t2s.write_run(run, Path("runs/v3.json"))
    >>> t2s.write_html_report(run, Path("runs/v3.html"), run_name="v3")
"""

from importlib.metadata import version

from text2sql_eval.compare.runs import (
    CaseChange,
    Change,
    Comparison,
    GroupEx,
    compare_runs,
    write_comparison_csv,
)
from text2sql_eval.errors import InputError
from text2sql_eval.evaluate import evaluate_files
from text2sql_eval.execution.executor import QueryFailure, SqlValue
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
from text2sql_eval.report.csv_report import write_report_csv
from text2sql_eval.report.html_report import write_html_report
from text2sql_eval.runfile import (
    CaseRecord,
    FileRef,
    PredictionState,
    ResultSample,
    Run,
    RunSettings,
    Summary,
    read_run,
    write_run,
)

__version__ = version("text2sql-eval")

# Sorted as Ruff requires; docs/reference/api.md groups them by purpose.
__all__ = [
    "CaseChange",
    "CaseDiff",
    "CaseRecord",
    "Change",
    "Comparison",
    "Correct",
    "ExecError",
    "Fact",
    "FactKind",
    "FileRef",
    "Flag",
    "FlagKind",
    "GroupEx",
    "Incorrect",
    "InputError",
    "OutputDiff",
    "OutputDifference",
    "PredictionState",
    "QueryFailure",
    "Relation",
    "ResultSample",
    "Run",
    "RunSettings",
    "SqlValue",
    "StructureReport",
    "Summary",
    "Verdict",
    "__version__",
    "compare_runs",
    "evaluate_files",
    "read_run",
    "status_of",
    "write_comparison_csv",
    "write_html_report",
    "write_report_csv",
    "write_run",
]
