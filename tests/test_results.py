"""The committed baseline results must stay reproducible from their predictions.

If judging changes, these tests fail instead of the published numbers in
examples/results/README.md silently drifting. They use the default 30 s
timeout: with 5 s, two no-evidence predictions (247, 281) that finish in about
18 s and 5 s would flip from incorrect to timeout.
"""

from pathlib import Path

import pytest

from text2sql_eval.datasets.bird import load_bird, load_bird_tied
from text2sql_eval.datasets.predictions import load_jsonl_predictions
from text2sql_eval.evaluate import evaluate
from text2sql_eval.judge.ex import status_of
from text2sql_eval.runfile import read_run

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize(("mode", "correct"), [("evidence", 267), ("no-evidence", 162)])
def test_committed_run_is_reproduced_from_its_predictions(
    mode: str, correct: int
) -> None:
    dataset = load_bird(EXAMPLES / "bird-mini/dev.json")
    tied = load_bird_tied(EXAMPLES / "bird-mini/dev_tied_append.json", dataset)
    predictions = load_jsonl_predictions(
        EXAMPLES / f"results/gpt-4o-mini-{mode}.jsonl", dataset
    )
    committed = read_run(EXAMPLES / f"results/gpt-4o-mini-{mode}.run.json")

    records = evaluate(
        dataset, predictions, db_dir=EXAMPLES / "bird-mini/dev_databases", tied=tied
    )

    assert committed.summary.correct == correct
    assert [
        (r.id, status_of(r.verdict), [f.kind for f in r.verdict.flags]) for r in records
    ] == [
        (c.id, status_of(c.verdict), [f.kind for f in c.verdict.flags])
        for c in committed.cases
    ]
