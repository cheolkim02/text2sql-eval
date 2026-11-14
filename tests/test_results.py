"""The committed baseline results must stay reproducible from their predictions.

If judging changes, these tests fail instead of the published numbers in
examples/results/README.md silently drifting.

A few predictions are left out because their verdict depends on machine speed,
not on judging (see "시간 제한에 민감한 케이스" in that README): 211 never
finishes, and 247 and 281 take about 18 s and 5 s. On a slower machine 247
crosses the 30 s limit; it did on a GitHub Actions runner (PR #8), turning
"incorrect" into a timeout error. Re-running them would test hardware.
"""

from pathlib import Path

import pytest

from text2sql_eval.datasets.bird import Dataset, load_bird, load_bird_tied
from text2sql_eval.datasets.predictions import load_jsonl_predictions
from text2sql_eval.evaluate import evaluate
from text2sql_eval.judge.ex import status_of
from text2sql_eval.report.html_report import render_html
from text2sql_eval.runfile import read_run

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

TIMING_SENSITIVE = {"evidence": {"211"}, "no-evidence": {"247", "281"}}


@pytest.mark.parametrize(("mode", "correct"), [("evidence", 267), ("no-evidence", 162)])
def test_committed_run_is_reproduced_from_its_predictions(
    mode: str, correct: int
) -> None:
    full = load_bird(EXAMPLES / "bird-mini/dev.json")
    tied = load_bird_tied(EXAMPLES / "bird-mini/dev_tied_append.json", full)
    predictions = load_jsonl_predictions(
        EXAMPLES / f"results/gpt-4o-mini-{mode}.jsonl", full
    )
    committed = read_run(EXAMPLES / f"results/gpt-4o-mini-{mode}.run.json")
    skip = TIMING_SENSITIVE[mode]
    dataset = Dataset(
        path=full.path, cases=tuple(c for c in full.cases if c.id not in skip)
    )

    records = evaluate(
        dataset, predictions, db_dir=EXAMPLES / "bird-mini/dev_databases", tied=tied
    )

    assert committed.summary.correct == correct
    assert [
        (r.id, status_of(r.verdict), [f.kind for f in r.verdict.flags]) for r in records
    ] == [
        (c.id, status_of(c.verdict), [f.kind for f in c.verdict.flags])
        for c in committed.cases
        if c.id not in skip
    ]


def test_timing_sensitive_cases_are_the_documented_ones() -> None:
    # Keep the skip list honest: these are exactly the slow predictions the
    # README describes, with the verdicts recorded on the machine that made them.
    expected = {
        ("evidence", "211"): "error",
        ("no-evidence", "247"): "incorrect",
        ("no-evidence", "281"): "incorrect",
    }
    for (mode, case_id), status in expected.items():
        run = read_run(EXAMPLES / f"results/gpt-4o-mini-{mode}.run.json")
        (case,) = [c for c in run.cases if c.id == case_id]
        assert status_of(case.verdict) == status
    assert {(m, i) for m, ids in TIMING_SENSITIVE.items() for i in ids} == set(expected)


def test_committed_report_is_the_report_of_the_committed_run() -> None:
    # Regenerate with `text2sql-eval report` after changing the report code.
    run_file = EXAMPLES / "results/gpt-4o-mini-evidence.run.json"
    committed = (EXAMPLES / "results/report.html").read_text(encoding="utf-8")

    assert committed == render_html(read_run(run_file), run_name=run_file.name)
