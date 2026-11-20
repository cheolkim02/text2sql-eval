"""End-to-end tests that run ``text2sql-eval`` as a real process."""

import csv
import json
import re
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from helpers import run_cli

from text2sql_eval.runfile import read_run

BIRD_MINI = Path(__file__).resolve().parents[1] / "examples/bird-mini"
DEV = BIRD_MINI / "dev.json"


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
    assert "Output difference:" not in result.stdout  # nothing wrong
    assert "SQL structure difference:" not in result.stdout
    run = read_run(out)
    assert run.summary.correct == 432
    assert run.prediction_format == "text"
    assert run.meta == {"model": "gold", "note": "a=b"}
    assert run.tied is not None


def test_counts_one_case_in_the_singular(
    tmp_path: Path, gold_rows: list[dict[str, object]]
) -> None:
    dataset = tmp_path / "one.json"
    dataset.write_text(json.dumps(gold_rows[:1]), encoding="utf-8")
    pred = tmp_path / "one.txt"
    pred.write_text(f"{gold_rows[0]['SQL']}\n", encoding="utf-8")
    run = tmp_path / "one-run.json"

    evaluated = run_cli(
        "eval",
        "--dataset",
        dataset,
        "--db-dir",
        BIRD_MINI / "dev_databases",
        "--pred",
        pred,
        "--out",
        run,
    )
    reported = run_cli("report", run, "--csv", tmp_path / "one.csv")

    assert "Evaluated 1 case: EX 100.0%" in evaluated.stdout, evaluated.stderr
    assert ": 1 case, EX 100.0%" in reported.stdout, reported.stderr


def test_out_that_is_a_folder_fails_before_evaluating(tmp_path: Path) -> None:
    # The prediction file does not exist either; the folder is reported first,
    # so a long run is not lost at the end.
    result = run_cli(*eval_args(tmp_path / "missing.jsonl", tmp_path))

    assert result.returncode == 3  # the code for an unwritable output
    assert "Is a directory" in result.stderr
    assert "missing.jsonl" not in result.stderr


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
    # Every missing prediction returns no rows against a non-empty gold result.
    assert summary["output_differences"] == {"empty_result": 432 - len(half)}
    assert summary["sql_structure_differences"] == {}
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
    assert re.search(r"\(\d+ correct, \d+ incorrect, \d+ errors?\)", result.stdout)


RESULTS = BIRD_MINI.parent / "results"
NO_EVIDENCE = RESULTS / "gpt-4o-mini-no-evidence.run.json"
EVIDENCE = RESULTS / "gpt-4o-mini-evidence.run.json"


# --- report ------------------------------------------------------------------


def test_report_writes_html_and_csv_of_the_committed_run(tmp_path: Path) -> None:
    out = tmp_path / "evidence.csv"
    page = tmp_path / "evidence.html"

    result = run_cli("report", EVIDENCE, "--html", page, "--csv", out)

    assert result.returncode == 0, result.stderr
    assert "432 cases, EX 61.8%" in result.stdout
    assert f"HTML: {page}" in result.stdout
    assert f"CSV: {out}" in result.stdout
    html = page.read_text(encoding="utf-8")
    assert "gpt-4o-mini-evidence.run.json" in html
    with out.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 432
    assert sum(row["status"] == "correct" for row in rows) == 267


def test_report_without_an_output_is_a_usage_error() -> None:
    result = run_cli("report", EVIDENCE)

    assert result.returncode == 2
    assert "nothing to write" in result.stderr


def test_report_to_an_unwritable_path_is_an_environment_error(tmp_path: Path) -> None:
    taken = tmp_path / "already-a-directory"
    taken.mkdir()

    result = run_cli("report", EVIDENCE, "--html", taken)

    assert result.returncode == 3
    assert "error:" in result.stderr


def test_report_of_a_file_that_is_not_a_run_is_an_input_error(tmp_path: Path) -> None:
    result = run_cli("report", DEV, "--csv", tmp_path / "out.csv")

    assert result.returncode == 2
    assert "error:" in result.stderr
    assert not (tmp_path / "out.csv").exists()


# --- compare -----------------------------------------------------------------


def test_compare_summarizes_the_committed_baselines(tmp_path: Path) -> None:
    flips = tmp_path / "flips.csv"

    result = run_cli("compare", NO_EVIDENCE, EVIDENCE, "--csv", flips)

    assert result.returncode == 0, result.stderr
    assert "(432 common cases)" in result.stdout
    assert "EX: 37.5% -> 61.8% (+24.3 pp)" in result.stdout
    assert (
        "Both correct 144 | Fixed 123 | Regressed 18 | Both wrong 147" in result.stdout
    )
    assert "By difficulty: challenging 29.1% -> 47.3%" in result.stdout
    assert "where_value 129 -> 22" in result.stdout
    assert "WARNING" not in result.stdout
    # Count records with a CSV reader: some BIRD fields contain line breaks.
    with flips.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 432
    assert sum(row["change"] == "fixed" for row in rows) == 123


def test_compare_json_lists_flipped_cases() -> None:
    result = run_cli("compare", NO_EVIDENCE, EVIDENCE, "--json")

    summary = json.loads(result.stdout)
    assert (summary["fixed"], summary["regressed"]) == (123, 18)
    assert len(summary["fixed_ids"]) == 123
    assert summary["output_differences"]["base"]["empty_result"] == 100
    assert summary["failed_max_drop"] is False


@pytest.mark.parametrize(("max_drop", "code"), [("5", 1), ("30", 0)])
def test_compare_max_drop_fails_only_past_the_limit(max_drop: str, code: int) -> None:
    result = run_cli("compare", EVIDENCE, NO_EVIDENCE, "--max-drop", max_drop)

    assert result.returncode == code
    if code == 1:
        assert "FAILED: EX dropped by 24.3 pp, more than --max-drop 5" in result.stderr


def test_compare_without_max_drop_never_fails_on_a_drop() -> None:
    assert run_cli("compare", EVIDENCE, NO_EVIDENCE).returncode == 0


def test_compare_warns_about_a_different_dataset(tmp_path: Path) -> None:
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    document["inputs"]["dataset"]["sha256"] = "0" * 64
    document["cases"] = document["cases"][:100]
    head = tmp_path / "head.json"
    head.write_text(json.dumps(document), encoding="utf-8")

    result = run_cli("compare", NO_EVIDENCE, head)

    assert result.returncode == 0, result.stderr
    assert "WARNING: the runs used different dataset files" in result.stdout
    assert "WARNING: 332 cases only in base, left out" in result.stdout
    assert "(100 common cases)" in result.stdout


def test_compare_refuses_runs_without_common_cases(tmp_path: Path) -> None:
    document = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for record in document["cases"]:
        record["id"] = "x" + record["id"]
    head = tmp_path / "head.json"
    head.write_text(json.dumps(document), encoding="utf-8")

    result = run_cli("compare", NO_EVIDENCE, head)

    assert result.returncode == 2
    assert "shares no case ids" in result.stderr


def test_compare_rejects_a_negative_max_drop() -> None:
    result = run_cli("compare", EVIDENCE, NO_EVIDENCE, "--max-drop", "-1")

    assert result.returncode == 2
    assert "argument --max-drop: must be 0 or more" in result.stderr
