"""The whole flow as a user runs it: eval -> report -> compare, as real processes.

Each step's numbers must agree with the others: the eval summary, the run
file, the report's CSV and HTML, and the comparison. Only the first
predictions of the committed baselines are given (the rest are judged as
missing) so the test takes seconds; the slow predictions documented in
examples/results/README.md are left out.
"""

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pytest
from helpers import run_cli

from text2sql_eval import Run, read_run, status_of

ROOT = Path(__file__).resolve().parents[1]
BIRD_MINI = ROOT / "examples/bird-mini"
RESULTS = ROOT / "examples/results"
SLOW = {"211", "247", "281"}  # "시간 제한에 민감한 케이스" in that README
FIRST = 40


@dataclass(frozen=True)
class Evaluated:
    path: Path
    run: Run
    summary: dict[str, object]  # what `eval --json` printed
    given: int


def first_predictions(mode: str, out: Path) -> int:
    lines = (RESULTS / f"gpt-4o-mini-{mode}.jsonl").read_text(encoding="utf-8")
    kept = [
        line
        for line in lines.splitlines()[:FIRST]
        if str(json.loads(line)["id"]) not in SLOW
    ]
    out.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return len(kept)


def evaluate(mode: str, tmp_path: Path) -> Evaluated:
    pred = tmp_path / f"{mode}.jsonl"
    given = first_predictions(mode, pred)
    path = tmp_path / "runs" / f"{mode}.json"
    result = run_cli(
        "eval",
        "--dataset",
        BIRD_MINI / "dev.json",
        "--db-dir",
        BIRD_MINI / "dev_databases",
        "--pred",
        pred,
        "--tied",
        BIRD_MINI / "dev_tied_append.json",
        "--allow-missing",
        "--timeout",
        "10",
        "--meta",
        f"evidence={mode}",
        "--out",
        path,
        "--json",
    )
    assert result.returncode == 0, result.stderr
    summary: dict[str, object] = json.loads(result.stdout)
    return Evaluated(path, read_run(path), summary, given)


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Evaluated]:
    tmp_path = tmp_path_factory.mktemp("e2e")
    return {mode: evaluate(mode, tmp_path) for mode in ("evidence", "no-evidence")}


@pytest.mark.parametrize("mode", ["evidence", "no-evidence"])
def test_eval_summary_matches_the_run_file(
    runs: dict[str, Evaluated], mode: str
) -> None:
    evaluated = runs[mode]
    summary, run = evaluated.summary, evaluated.run

    assert summary["run_file"] == str(evaluated.path)
    assert (summary["total"], summary["correct"], summary["incorrect"]) == (
        run.summary.total,
        run.summary.correct,
        run.summary.incorrect,
    )
    assert summary["error"] == run.summary.error
    assert summary["missing_predictions"] == 432 - evaluated.given
    assert run.meta == {"evidence": mode}


def test_report_csv_and_html_agree_with_the_run(
    runs: dict[str, Evaluated], tmp_path: Path
) -> None:
    evaluated = runs["evidence"]
    page, sheet = tmp_path / "report.html", tmp_path / "report.csv"

    result = run_cli("report", evaluated.path, "--html", page, "--csv", sheet)

    assert result.returncode == 0, result.stderr
    ex = f"{evaluated.run.summary.ex:.1%}"
    assert f"432 cases, EX {ex}" in result.stdout
    with sheet.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert Counter(row["status"] for row in rows) == Counter(
        status_of(case.verdict) for case in evaluated.run.cases
    )
    html = page.read_text(encoding="utf-8")
    assert html.count('<details class="case"') == len(rows) == 432
    assert f'<div class="ex">{ex}</div>' in html


def test_compare_agrees_with_both_runs(
    runs: dict[str, Evaluated], tmp_path: Path
) -> None:
    base, head = runs["no-evidence"], runs["evidence"]
    flips = tmp_path / "flips.csv"

    result = run_cli("compare", base.path, head.path, "--json", "--csv", flips)

    assert result.returncode == 0, result.stderr
    comparison: dict[str, object] = json.loads(result.stdout)
    assert comparison["common_cases"] == 432
    assert comparison["dataset_mismatch"] is False
    assert comparison["base_ex"] == base.run.summary.ex
    assert comparison["head_ex"] == head.run.summary.ex
    fixed, regressed = comparison["fixed"], comparison["regressed"]
    assert isinstance(fixed, int) and isinstance(regressed, int)
    assert fixed - regressed == head.run.summary.correct - base.run.summary.correct
    with flips.open(encoding="utf-8-sig", newline="") as file:
        assert sum(1 for _ in csv.DictReader(file)) == 432


@pytest.mark.parametrize("command", ["eval", "report", "compare"])
def test_help_examples_name_files_that_exist(command: str) -> None:
    result = run_cli(command, "--help")

    paths = re.findall(r"examples/[\w./-]+", result.stdout)
    assert paths, "each command's help shows an example with the repository data"
    for path in paths:
        assert (ROOT / path).exists(), path
