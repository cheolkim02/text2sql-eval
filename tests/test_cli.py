"""End-to-end tests that run ``text2sql-eval`` as a real process."""

import json
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from text2sql_eval.runfile import read_run

BIRD_MINI = Path(__file__).resolve().parents[1] / "examples/bird-mini"
DEV = BIRD_MINI / "dev.json"


def run_cli(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "text2sql_eval.cli.main", *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def eval_args(pred: Path, out: Path, *extra: str | Path) -> list[str | Path]:
    return [
        "eval",
        "--dataset",
        DEV,
        "--db-dir",
        BIRD_MINI / "dev_databases",
        "--pred",
        pred,
        "--out",
        out,
        *extra,
    ]


@pytest.fixture(scope="module")
def gold_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = json.loads(DEV.read_text(encoding="utf-8"))
    return rows


def test_console_script_points_at_main() -> None:
    (script,) = entry_points(group="console_scripts", name="text2sql-eval")

    assert script.value == "text2sql_eval.cli.main:main"


def test_eval_with_text_predictions_writes_a_run_file(
    tmp_path: Path, gold_rows: list[dict[str, object]]
) -> None:
    pred = tmp_path / "gold.txt"
    pred.write_text("".join(f"{row['SQL']}\n" for row in gold_rows), encoding="utf-8")
    out = tmp_path / "runs" / "gold.json"

    result = run_cli(
        *eval_args(
            pred,
            out,
            "--tied",
            BIRD_MINI / "dev_tied_append.json",
            "--meta",
            "model=gold",
            "--meta",
            "note=a=b",
        )
    )

    assert result.returncode == 0, result.stderr
    assert "Evaluated 432 cases: EX 100.0% (432 correct" in result.stdout
    assert "13 tied_alternative_exists" in result.stdout
    assert "Predictions:" not in result.stdout  # nothing missing or empty
    run = read_run(out)
    assert run.summary.correct == 432
    assert run.prediction_format == "text"
    assert run.meta == {"model": "gold", "note": "a=b"}
    assert run.tied is not None


def test_eval_with_jsonl_predictions_and_allow_missing_prints_json(
    tmp_path: Path, gold_rows: list[dict[str, object]]
) -> None:
    pred = tmp_path / "half.jsonl"
    half = gold_rows[::2]
    pred.write_text(
        "".join(
            json.dumps({"id": r["question_id"], "sql": r["SQL"]}) + "\n" for r in half
        ),
        encoding="utf-8",
    )

    result = run_cli(
        *eval_args(pred, tmp_path / "half.json", "--allow-missing", "--json")
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["total"] == 432
    assert summary["correct"] == len(half)
    assert summary["missing_predictions"] == 432 - len(half)
    assert summary["empty_predictions"] == 0
    run = read_run(tmp_path / "half.json")
    assert sum(case.prediction_state == "missing" for case in run.cases) == 432 - len(
        half
    )


def test_pred_format_overrides_the_extension(
    tmp_path: Path, gold_rows: list[dict[str, object]]
) -> None:
    pred = tmp_path / "predictions.sql"
    pred.write_text("".join(f"{row['SQL']}\n" for row in gold_rows), encoding="utf-8")

    result = run_cli(*eval_args(pred, tmp_path / "r.json", "--pred-format", "text"))

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["eval", "--dataset", DEV], "the following arguments are required"),
        (["eval", "--timeout", "0"], "argument --timeout: must be greater than 0"),
        (["eval", "--workers", "two"], "argument --workers: not an integer"),
        (["eval", "--meta", "novalue"], "argument --meta: expected KEY=VALUE"),
        (["nope"], "invalid choice: 'nope'"),
    ],
)
def test_usage_errors_exit_with_code_2(args: list[str], message: str) -> None:
    result = run_cli(*args)

    assert result.returncode == 2
    assert message in result.stderr


def test_unknown_extension_explains_how_to_fix_it(tmp_path: Path) -> None:
    result = run_cli(*eval_args(tmp_path / "p.csv", tmp_path / "r.json"))

    assert result.returncode == 2
    assert (
        "cannot tell the prediction format from the extension '.csv'" in result.stderr
    )
    assert "pass --pred-format text|jsonl" in result.stderr


def test_allow_missing_is_rejected_for_text_predictions(tmp_path: Path) -> None:
    pred = tmp_path / "p.txt"
    pred.write_text("SELECT 1\n", encoding="utf-8")

    result = run_cli(*eval_args(pred, tmp_path / "r.json", "--allow-missing"))

    assert result.returncode == 2
    assert "--allow-missing only applies to JSONL predictions" in result.stderr


def test_input_errors_exit_with_code_2_and_name_the_line(tmp_path: Path) -> None:
    pred = tmp_path / "p.jsonl"
    pred.write_text('{"id": 195, "sql": "SELECT 1"}\n{"id": 195}\n', encoding="utf-8")

    result = run_cli(*eval_args(pred, tmp_path / "r.json"))

    assert result.returncode == 2
    assert "line 2: missing field 'sql'" in result.stderr
    assert not (tmp_path / "r.json").exists()


def test_missing_database_folder_is_reported(tmp_path: Path) -> None:
    pred = tmp_path / "p.jsonl"
    pred.write_text("", encoding="utf-8")
    args = eval_args(pred, tmp_path / "r.json", "--allow-missing")
    args[args.index("--db-dir") + 1] = tmp_path / "nowhere"

    result = run_cli(*args)

    assert result.returncode == 2
    assert "database file not found" in result.stderr
    assert "<db-dir>/<db_id>/<db_id>.sqlite" in result.stderr


def test_unwritable_output_is_an_environment_error(
    tmp_path: Path, gold_rows: list[dict[str, object]]
) -> None:
    pred = tmp_path / "gold.txt"
    pred.write_text("".join(f"{row['SQL']}\n" for row in gold_rows), encoding="utf-8")
    out = tmp_path / "already-a-directory"
    out.mkdir()

    result = run_cli(*eval_args(pred, out))

    assert result.returncode == 3
    assert "error:" in result.stderr


def test_text_summary_explains_missing_predictions(
    tmp_path: Path, gold_rows: list[dict[str, object]]
) -> None:
    pred = tmp_path / "few.jsonl"
    pred.write_text(
        json.dumps({"id": gold_rows[0]["question_id"], "sql": ""}) + "\n",
        encoding="utf-8",
    )

    result = run_cli(*eval_args(pred, tmp_path / "few.json", "--allow-missing"))

    assert result.returncode == 0, result.stderr
    assert "Predictions: 431 missing, 1 empty (judged as empty SQL)" in result.stdout
