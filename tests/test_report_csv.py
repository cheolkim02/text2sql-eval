import csv
from dataclasses import replace
from pathlib import Path

from text2sql_eval.execution.executor import QueryFailure
from text2sql_eval.facts import CaseDiff
from text2sql_eval.facts.output import OutputDiff
from text2sql_eval.facts.structure import Fact, StructureReport
from text2sql_eval.judge.ex import Correct, ExecError, Flag, Incorrect
from text2sql_eval.report.csv_report import CSV_COLUMNS, write_csv
from text2sql_eval.runfile import CaseRecord, FileRef, ResultSample, Run, RunSettings

SAMPLE = ResultSample(columns=("name",), rows=(("Surtur",),), row_count=1)

CORRECT = CaseRecord(
    id="1",
    db_id="superhero",
    difficulty="simple",
    question="불의 거인은 누구인가?",
    evidence="line one\nline two, with a comma",
    gold_sql="SELECT name FROM superhero",
    pred_sql="SELECT name FROM superhero",
    prediction_state="given",
    verdict=Correct(),
    gold=SAMPLE,
    pred=SAMPLE,
)

WRONG = replace(
    CORRECT,
    id="2",
    pred_sql="SELECT name, id FROM superhero",
    verdict=Incorrect(
        flags=(
            Flag("gold_rows_with_extra_columns", "extra columns"),
            Flag("tied_alternative_exists", "tied"),
        )
    ),
    diff=CaseDiff(
        output=OutputDiff(
            ("column_mismatch", "row_set_differs"),
            gold_columns=1,
            pred_columns=2,
            gold_distinct_rows=1,
            pred_distinct_rows=1,
        ),
        structure=StructureReport(facts=(Fact("columns", "(none)", "id"),)),
    ),
)

FAILED = replace(
    CORRECT,
    id="3",
    db_id="toxicology",
    difficulty=None,
    pred_sql="",
    prediction_state="missing",
    verdict=ExecError("pred", "timeout", "did not finish within 30 s"),
    pred=QueryFailure("timeout", "did not finish within 30 s"),
)


def make_run(*cases: CaseRecord) -> Run:
    return Run(
        tool_version="0.1.0",
        created_at="2026-11-11T00:00:00Z",
        dataset=FileRef("dev.json", "a" * 64),
        predictions=FileRef("p.jsonl", "b" * 64),
        prediction_format="jsonl",
        tied=None,
        db_dir="dbs",
        settings=RunSettings(timeout_seconds=30.0, max_rows=None, allow_missing=True),
        meta={},
        cases=cases,
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def test_one_row_per_case_in_run_order_with_a_bom(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "report.csv"

    write_csv(make_run(CORRECT, WRONG, FAILED), path)

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")  # Excel reads it as UTF-8
    rows = read_rows(path)
    assert list(rows[0]) == list(CSV_COLUMNS)
    assert [(r["id"], r["status"]) for r in rows] == [
        ("1", "correct"),
        ("2", "incorrect"),
        ("3", "error"),
    ]


def test_wrong_case_lists_differences_and_flags(tmp_path: Path) -> None:
    path = tmp_path / "report.csv"

    write_csv(make_run(WRONG), path)

    (row,) = read_rows(path)
    assert row["output_differences"] == "column_mismatch;row_set_differs"
    assert row["sql_structure_differences"] == "columns"
    assert row["flags"] == "gold_rows_with_extra_columns;tied_alternative_exists"
    assert row["error"] == ""
    assert (row["my_category"], row["notes"]) == ("", "")


def test_correct_case_has_empty_analysis_columns(tmp_path: Path) -> None:
    path = tmp_path / "report.csv"

    write_csv(make_run(CORRECT), path)

    (row,) = read_rows(path)
    assert row["output_differences"] == row["sql_structure_differences"] == ""
    assert row["flags"] == ""
    # Korean text, line breaks and commas survive the round trip.
    assert row["question"] == "불의 거인은 누구인가?"
    assert row["evidence"] == "line one\nline two, with a comma"


def test_failed_case_shows_the_error_and_prediction_state(tmp_path: Path) -> None:
    path = tmp_path / "report.csv"

    write_csv(make_run(FAILED), path)

    (row,) = read_rows(path)
    assert row["error"] == "pred timeout: did not finish within 30 s"
    assert row["prediction"] == "missing"
    assert row["difficulty"] == ""


def test_cells_that_start_like_a_formula_are_written_as_text(tmp_path: Path) -> None:
    path = tmp_path / "report.csv"
    hostile = replace(
        WRONG,
        pred_sql='=HYPERLINK("http://example.com","click")',
        evidence="-- the model's note",
        question="What is 1 = 1?",
    )

    write_csv(make_run(hostile), path)

    (row,) = read_rows(path)
    assert row["pred_sql"] == '\'=HYPERLINK("http://example.com","click")'
    assert row["evidence"] == "'-- the model's note"
    assert row["question"] == "What is 1 = 1?"  # only the first character counts
