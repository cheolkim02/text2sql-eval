"""The ``text2sql-eval`` command (ADR 0025).

Exit codes: 0 success, 1 judgement failure (used by ``compare`` later),
2 usage or input error, 3 environment error, 130 interrupted.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from text2sql_eval import __version__
from text2sql_eval.datasets.bird import load_bird, load_bird_tied
from text2sql_eval.datasets.predictions import (
    load_jsonl_predictions,
    load_text_predictions,
)
from text2sql_eval.errors import InputError
from text2sql_eval.evaluate import evaluate
from text2sql_eval.execution.executor import DEFAULT_TIMEOUT_SECONDS
from text2sql_eval.runfile import (
    FileRef,
    PredictionFormat,
    Run,
    RunSettings,
    sha256_of,
    write_run,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_ENVIRONMENT = 3
EXIT_INTERRUPTED = 130

_FORMAT_BY_SUFFIX: dict[str, PredictionFormat] = {".txt": "text", ".jsonl": "jsonl"}

_EVAL_EXAMPLES = """\
examples:
  text2sql-eval eval --dataset dev.json --db-dir dev_databases \\
      --pred predictions.txt --out runs/baseline.json
  text2sql-eval eval --dataset dev.json --db-dir dev_databases \\
      --pred predictions.jsonl --tied dev_tied_append.json \\
      --meta model=my-model --meta prompt=v3 --out runs/v3.json
"""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line. Returns the process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)  # exits with code 2 on usage errors
    try:
        if args.command == "eval":
            return _run_eval(args, sys.stdout)
        parser.error(f"unknown command {args.command!r}")
    except InputError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_USAGE
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
    return parser


def _run_eval(args: argparse.Namespace, out: TextIO) -> int:
    dataset_path: Path = args.dataset
    pred_path: Path = args.pred
    tied_path: Path | None = args.tied
    db_dir: Path = args.db_dir
    out_path: Path = args.out
    pred_format = _prediction_format(pred_path, args.pred_format)
    if args.allow_missing and pred_format != "jsonl":
        raise InputError(
            pred_path,
            "--allow-missing only applies to JSONL predictions",
            hint="text predictions need one line per case; leave a line empty instead",
        )

    dataset = load_bird(dataset_path)
    if pred_format == "text":
        predictions = load_text_predictions(pred_path, dataset)
    else:
        predictions = load_jsonl_predictions(
            pred_path, dataset, allow_missing=args.allow_missing
        )
    tied = None if tied_path is None else load_bird_tied(tied_path, dataset)

    records = evaluate(
        dataset,
        predictions,
        db_dir=db_dir,
        tied=tied,
        timeout=args.timeout,
        max_rows=args.max_rows,
        workers=args.workers,
    )
    run = Run(
        tool_version=__version__,
        created_at=datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        dataset=FileRef(str(dataset_path), sha256_of(dataset_path)),
        predictions=FileRef(str(pred_path), sha256_of(pred_path)),
        prediction_format=pred_format,
        tied=None
        if tied_path is None
        else FileRef(str(tied_path), sha256_of(tied_path)),
        db_dir=str(db_dir),
        settings=RunSettings(
            timeout_seconds=args.timeout,
            max_rows=args.max_rows,
            allow_missing=args.allow_missing,
        ),
        meta=dict(args.meta),
        cases=records,
    )
    write_run(run, out_path)
    _print_summary(run, out_path, out, as_json=args.json)
    return EXIT_OK


def _prediction_format(path: Path, override: str | None) -> PredictionFormat:
    if override == "text" or override == "jsonl":
        return override
    detected = _FORMAT_BY_SUFFIX.get(path.suffix.lower())
    if detected is None:
        raise InputError(
            path,
            f"cannot tell the prediction format from the extension '{path.suffix}'",
            hint="use a .txt or .jsonl file, or pass --pred-format text|jsonl",
        )
    return detected


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
        f"{summary.error} errors)",
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
