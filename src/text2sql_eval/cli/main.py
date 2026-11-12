"""The ``text2sql-eval`` command (ADR 0025).

Exit codes: 0 success, 1 a check failed (``compare --max-drop``),
2 usage or input error, 3 environment error, 130 interrupted.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, TextIO

from text2sql_eval import __version__
from text2sql_eval.compare.runs import (
    Comparison,
    compare_runs,
    write_comparison_csv,
)
from text2sql_eval.errors import InputError
from text2sql_eval.evaluate import evaluate_files
from text2sql_eval.execution.executor import DEFAULT_TIMEOUT_SECONDS
from text2sql_eval.report import csv_report, html_report
from text2sql_eval.runfile import PredictionFormat, Run, read_run, write_run

EXIT_OK = 0
EXIT_FAILED_CHECK = 1
EXIT_USAGE = 2
EXIT_ENVIRONMENT = 3
EXIT_INTERRUPTED = 130

_EVAL_EXAMPLES = """\
examples:
  # With the example data in this repository:
  text2sql-eval eval --dataset examples/bird-mini/dev.json \\
      --db-dir examples/bird-mini/dev_databases \\
      --pred examples/results/gpt-4o-mini-evidence.jsonl \\
      --tied examples/bird-mini/dev_tied_append.json --out runs/evidence.json

  # Your own predictions, one SQL per line in dataset order:
  text2sql-eval eval --dataset dev.json --db-dir dev_databases \\
      --pred predictions.txt --out runs/baseline.json

  # JSONL predictions, recording facts about the run:
  text2sql-eval eval --dataset dev.json --db-dir dev_databases \\
      --pred predictions.jsonl --meta model=my-model --meta prompt=v3 \\
      --out runs/v3.json
"""


_REPORT_EXAMPLES = """\
examples:
  # A committed run in this repository:
  text2sql-eval report examples/results/gpt-4o-mini-evidence.run.json \\
      --html runs/evidence.html --csv runs/evidence.csv

  text2sql-eval report runs/v3.json --html runs/v3.html
"""


_COMPARE_EXAMPLES = """\
examples:
  # The two committed runs in this repository:
  text2sql-eval compare examples/results/gpt-4o-mini-no-evidence.run.json \\
      examples/results/gpt-4o-mini-evidence.run.json

  # Fail (exit code 1) if EX drops by more than 1 percentage point:
  text2sql-eval compare runs/main.json runs/branch.json --max-drop 1.0 \\
      --csv runs/flips.csv
"""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line. Returns the process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)  # exits with code 2 on usage errors
    if args.command == "report" and args.html is None and args.csv is None:
        parser.error("report: nothing to write; pass --html PATH, --csv PATH or both")
    try:
        if args.command == "eval":
            return _run_eval(args, sys.stdout)
        if args.command == "report":
            return _run_report(args, sys.stdout)
        if args.command == "compare":
            return _run_compare(args, sys.stdout)
        parser.error(f"unknown command {args.command!r}")
    except InputError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except BrokenPipeError:
        # The reader went away (e.g. `| head`); that is not our error.
        _silence_stdout()
        return EXIT_OK
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ENVIRONMENT
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="text2sql-eval",
        description="Judge text-to-SQL predictions and explain what went wrong.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    run = commands.add_parser(
        "eval",
        help="execute and judge predictions, and write a run file",
        description="Execute gold and predicted SQL, judge EX like BIRD's "
        "official script, and write the results to a JSON run file.",
        epilog=_EVAL_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run.add_argument("--dataset", type=Path, required=True, help="BIRD question file")
    run.add_argument(
        "--db-dir",
        type=Path,
        required=True,
        help="folder holding <db_id>/<db_id>.sqlite",
    )
    run.add_argument(
        "--pred",
        type=Path,
        required=True,
        help="predictions: .txt (one SQL per line) or .jsonl",
    )
    run.add_argument(
        "--pred-format",
        choices=("text", "jsonl"),
        help="override the format implied by the --pred file extension",
    )
    run.add_argument(
        "--allow-missing",
        action="store_true",
        help="JSONL only: judge cases without a line as empty predictions",
    )
    run.add_argument(
        "--tied",
        type=Path,
        help="BIRD tied-rows alternative gold file, used for flags only",
    )
    run.add_argument("--out", type=Path, required=True, help="run file to write")
    run.add_argument(
        "--timeout",
        type=_positive_float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="seconds allowed per query (default: %(default)g)",
    )
    run.add_argument(
        "--max-rows",
        type=_positive_int,
        help="fail queries returning more rows than this (default: no limit)",
    )
    run.add_argument(
        "--workers", type=_positive_int, help="parallel queries (default: min(8, CPUs))"
    )
    run.add_argument(
        "--meta",
        action="append",
        default=[],
        type=_key_value,
        metavar="KEY=VALUE",
        help="record a fact about this run, such as model=... (repeatable)",
    )
    run.add_argument(
        "--json", action="store_true", help="print the summary as JSON on stdout"
    )

    report = commands.add_parser(
        "report",
        help="write an HTML and/or CSV report of a run file",
        description="Write a run file as a single-file HTML report that opens "
        "offline, and/or as a CSV file for spreadsheet analysis.",
        epilog=_REPORT_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    report.add_argument("run", type=Path, help="run file written by eval")
    report.add_argument("--html", type=Path, help="write the HTML report to this file")
    report.add_argument(
        "--csv",
        type=Path,
        help="write one row per case to this CSV file (UTF-8 with BOM for Excel)",
    )

    compare = commands.add_parser(
        "compare",
        help="compare two run files case by case",
        description="Compare two run files over the cases they share: which "
        "cases both got right, which only one got right, and how the kinds of "
        "differences changed.",
        epilog=_COMPARE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    compare.add_argument("base", type=Path, help="run file to compare from")
    compare.add_argument("head", type=Path, help="run file to compare to")
    compare.add_argument(
        "--max-drop",
        type=_non_negative_float,
        metavar="PP",
        help="exit with code 1 if EX drops by more than PP percentage points "
        "(default: never fail)",
    )
    compare.add_argument(
        "--csv", type=Path, help="write one row per common case to this CSV file"
    )
    compare.add_argument(
        "--json", action="store_true", help="print the summary as JSON on stdout"
    )
    return parser


def _run_eval(args: argparse.Namespace, out: TextIO) -> int:
    out_path: Path = args.out
    pred_format: PredictionFormat | None = args.pred_format
    run = evaluate_files(
        args.dataset,
        args.pred,
        db_dir=args.db_dir,
        prediction_format=pred_format,
        allow_missing=args.allow_missing,
        tied=args.tied,
        timeout=args.timeout,
        max_rows=args.max_rows,
        workers=args.workers,
        meta=dict(args.meta),
    )
    write_run(run, out_path)
    _print_summary(run, out_path, out, as_json=args.json)
    return EXIT_OK


def _run_report(args: argparse.Namespace, out: TextIO) -> int:
    run_path: Path = args.run
    html_path: Path | None = args.html
    csv_path: Path | None = args.csv
    run = read_run(run_path)
    if html_path is not None:
        html_report.write_html_report(run, html_path, run_name=run_path.name)
    if csv_path is not None:
        csv_report.write_report_csv(run, csv_path)
    summary = run.summary
    print(f"Report of {run_path}: {summary.total} cases, EX {summary.ex:.1%}", file=out)
    if html_path is not None:
        print(f"HTML: {html_path}", file=out)
    if csv_path is not None:
        print(f"CSV: {csv_path}", file=out)
    return EXIT_OK


def _run_compare(args: argparse.Namespace, out: TextIO) -> int:
    base_path: Path = args.base
    head_path: Path = args.head
    comparison = compare_runs(read_run(base_path), read_run(head_path))
    if not comparison.cases:
        raise InputError(
            head_path,
            f"shares no case ids with {base_path}",
            hint="compare runs made on the same dataset",
        )
    csv_path: Path | None = args.csv
    if csv_path is not None:
        write_comparison_csv(comparison, csv_path)

    max_drop: float | None = args.max_drop
    failed = max_drop is not None and comparison.delta_pp < -max_drop
    try:
        if args.json:
            _print_comparison_json(comparison, out, failed=failed)
        else:
            _print_comparison(comparison, base_path, head_path, out)
            if csv_path is not None:
                print(f"CSV: {csv_path}", file=out)
    except BrokenPipeError:
        # Output cut short (e.g. `| head`) must not hide a failed --max-drop.
        _silence_stdout()
    if failed:
        print(
            f"FAILED: EX dropped by {-comparison.delta_pp:.1f} pp, "
            f"more than --max-drop {max_drop:g}",
            file=sys.stderr,
        )
        return EXIT_FAILED_CHECK
    return EXIT_OK


def _print_comparison(
    comparison: Comparison, base_path: Path, head_path: Path, out: TextIO
) -> None:
    if comparison.dataset_mismatch:
        print(
            "WARNING: the runs used different dataset files (SHA-256 differs); "
            "comparing only the cases both have",
            file=out,
        )
    for label, ids in (
        ("base", comparison.only_in_base),
        ("head", comparison.only_in_head),
    ):
        if ids:
            print(f"WARNING: {len(ids)} cases only in {label}, left out", file=out)
    counts = comparison.counts()
    print(
        f"Comparing {base_path} -> {head_path} ({len(comparison.cases)} common cases)",
        file=out,
    )
    print(
        f"EX: {comparison.base_ex:.1%} -> {comparison.head_ex:.1%} "
        f"({comparison.delta_pp:+.1f} pp)",
        file=out,
    )
    print(
        f"Both correct {counts['both_correct']} | Fixed {counts['fixed']} | "
        f"Regressed {counts['regressed']} | Both wrong {counts['both_wrong']}",
        file=out,
    )
    groupings: tuple[tuple[Literal["difficulty", "db_id"], str], ...] = (
        ("difficulty", "By difficulty"),
        ("db_id", "By database"),
    )
    for key, title in groupings:
        listing = ", ".join(
            f"{g.name} {g.base_ex:.1%} -> {g.head_ex:.1%}" for g in comparison.by(key)
        )
        print(f"{title}: {listing}", file=out)
    for title, (base, head) in (
        ("Output difference", comparison.output_differences()),
        ("SQL structure difference", comparison.structure_differences()),
    ):
        kinds = sorted(set(base) | set(head), key=lambda k: (-base[k], k))
        if kinds:
            listing = ", ".join(f"{k} {base[k]} -> {head[k]}" for k in kinds)
            print(f"{title}: {listing}", file=out)


def _print_comparison_json(
    comparison: Comparison, out: TextIO, *, failed: bool
) -> None:
    counts = comparison.counts()
    output_base, output_head = comparison.output_differences()
    structure_base, structure_head = comparison.structure_differences()
    document = {
        "common_cases": len(comparison.cases),
        "dataset_mismatch": comparison.dataset_mismatch,
        "only_in_base": list(comparison.only_in_base),
        "only_in_head": list(comparison.only_in_head),
        "base_ex": comparison.base_ex,
        "head_ex": comparison.head_ex,
        "delta_pp": comparison.delta_pp,
        "both_correct": counts["both_correct"],
        "fixed": counts["fixed"],
        "regressed": counts["regressed"],
        "both_wrong": counts["both_wrong"],
        "fixed_ids": [c.base.id for c in comparison.cases if c.change == "fixed"],
        "regressed_ids": [
            c.base.id for c in comparison.cases if c.change == "regressed"
        ],
        "output_differences": {
            "base": dict(sorted(output_base.items())),
            "head": dict(sorted(output_head.items())),
        },
        "sql_structure_differences": {
            "base": dict(sorted(structure_base.items())),
            "head": dict(sorted(structure_head.items())),
        },
        "failed_max_drop": failed,
    }
    print(json.dumps(document), file=out)


def _silence_stdout() -> None:
    """Point stdout at devnull so the interpreter's final flush does not raise."""
    os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())


def _print_summary(run: Run, out_path: Path, out: TextIO, *, as_json: bool) -> None:
    summary = run.summary
    flags = Counter(flag.kind for case in run.cases for flag in case.verdict.flags)
    states = Counter(case.prediction_state for case in run.cases)
    outputs = Counter(
        difference
        for case in run.cases
        if case.diff is not None
        for difference in case.diff.output.differences
    )
    facts = Counter(
        fact.kind
        for case in run.cases
        if case.diff is not None
        for fact in case.diff.structure.facts
    )
    if as_json:
        document = {
            "run_file": str(out_path),
            "total": summary.total,
            "correct": summary.correct,
            "incorrect": summary.incorrect,
            "error": summary.error,
            "ex": summary.ex,
            "missing_predictions": states["missing"],
            "empty_predictions": states["empty"],
            "flags": dict(sorted(flags.items())),
            "output_differences": dict(sorted(outputs.items())),
            "sql_structure_differences": dict(sorted(facts.items())),
        }
        print(json.dumps(document), file=out)
        return
    print(
        f"Evaluated {summary.total} cases: EX {summary.ex:.1%} "
        f"({summary.correct} correct, {summary.incorrect} incorrect, "
        f"{summary.error} {'error' if summary.error == 1 else 'errors'})",
        file=out,
    )
    if states["missing"] or states["empty"]:
        # Both are judged as empty SQL (ADR 0023); say so, or the incorrect
        # count looks like model mistakes.
        print(
            f"Predictions: {states['missing']} missing, {states['empty']} empty "
            "(judged as empty SQL)",
            file=out,
        )
    # Counts are per kind; one wrong case can have several of each.
    if outputs:
        listing = ", ".join(f"{count} {kind}" for kind, count in outputs.most_common())
        print(f"Output difference: {listing}", file=out)
    if facts:
        listing = ", ".join(f"{count} {kind}" for kind, count in facts.most_common())
        print(f"SQL structure difference: {listing}", file=out)
    if flags:
        listing = ", ".join(f"{count} {kind}" for kind, count in sorted(flags.items()))
        print(f"Flags: {listing}", file=out)
    print(f"Run file: {out_path}", file=out)


def _positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not value > 0:
        raise argparse.ArgumentTypeError(f"must be greater than 0, got {text}")
    return value


def _non_negative_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not value >= 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more, got {text}")
    return value


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {text}")
    return value


def _key_value(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"expected KEY=VALUE, got {text!r}")
    return key, value


if __name__ == "__main__":
    sys.exit(main())
