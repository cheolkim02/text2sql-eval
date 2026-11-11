import csv
from dataclasses import replace
from pathlib import Path

from text2sql_eval.compare.runs import CSV_COLUMNS, compare_runs, write_csv
from text2sql_eval.execution.executor import QueryFailure
from text2sql_eval.facts import CaseDiff
from text2sql_eval.facts.output import OutputDiff
from text2sql_eval.facts.structure import Fact, StructureReport
from text2sql_eval.judge.ex import Correct, ExecError, Incorrect
from text2sql_eval.runfile import (
    CaseRecord,
    FileRef,
    ResultSample,
    Run,
    RunSettings,
)

SAMPLE = ResultSample(columns=("c",), rows=((1,),), row_count=1)

CASE = CaseRecord(
    id="1",
    db_id="superhero",
    difficulty="simple",
    question="질문",
    evidence="",
    gold_sql="SELECT 1",
    pred_sql="SELECT 1",
    prediction_state="given",
    verdict=Correct(),
    gold=SAMPLE,
    pred=SAMPLE,
)

WRONG = CaseDiff(
    output=OutputDiff(
        ("empty_result",),
        gold_columns=1,
        pred_columns=1,
        gold_distinct_rows=1,
        pred_distinct_rows=0,
    ),
    structure=StructureReport(facts=(Fact("where_value", "a = 'X'", "a = 'x'"),)),
)


def case(case_id: str, correct: bool, **overrides: object) -> CaseRecord:
    record = replace(CASE, id=case_id, **overrides)
    if correct:
        return replace(record, verdict=Correct(), diff=None)
    return replace(record, verdict=Incorrect(), diff=WRONG)


def run(*cases: CaseRecord, dataset_hash: str = "a" * 64) -> Run:
    return Run(
        tool_version="0.1.0",
        created_at="2026-11-11T00:00:00Z",
        dataset=FileRef("dev.json", dataset_hash),
        predictions=FileRef("p.jsonl", "b" * 64),
        prediction_format="jsonl",
        tied=None,
        db_dir="dbs",
        settings=RunSettings(timeout_seconds=30.0, max_rows=None, allow_missing=False),
        meta={},
        cases=cases,
    )


def test_contingency_and_ex_over_common_cases() -> None:
    base = run(case("1", True), case("2", True), case("3", False), case("4", False))
    head = run(case("1", True), case("2", False), case("3", True), case("4", False))

    comparison = compare_runs(base, head)

    assert comparison.counts() == {
        "both_correct": 1,
        "regressed": 1,
        "fixed": 1,
        "both_wrong": 1,
    }
    assert [c.change for c in comparison.cases] == [
        "both_correct",
        "regressed",
        "fixed",
        "both_wrong",
    ]
    assert (comparison.base_ex, comparison.head_ex, comparison.delta_pp) == (
        0.5,
        0.5,
        0.0,
    )


def test_errors_count_as_not_correct() -> None:
    failed = replace(
        case("1", False),
        verdict=ExecError("pred", "timeout", "did not finish within 30 s"),
        pred=QueryFailure("timeout", "did not finish within 30 s"),
    )

    comparison = compare_runs(run(failed), run(case("1", True)))

    assert comparison.counts() == {"fixed": 1}


def test_only_common_cases_are_compared_and_the_rest_reported() -> None:
    base = run(case("1", True), case("2", True))
    head = run(case("2", False), case("3", True), dataset_hash="c" * 64)

    comparison = compare_runs(base, head)

    assert [c.base.id for c in comparison.cases] == ["2"]
    assert comparison.only_in_base == ("1",)
    assert comparison.only_in_head == ("3",)
    assert comparison.dataset_mismatch is True
    assert comparison.delta_pp == -100.0


def test_groups_by_difficulty_and_database() -> None:
    base = run(
        case("1", True, difficulty="simple"),
        case("2", False, difficulty="moderate", db_id="toxicology"),
        case("3", False, difficulty=None),
    )
    head = run(
        case("1", True, difficulty="simple"),
        case("2", True, difficulty="moderate", db_id="toxicology"),
        case("3", False, difficulty=None),
    )

    comparison = compare_runs(base, head)

    by_difficulty = {
        g.name: (g.cases, g.base_ex, g.head_ex) for g in comparison.by("difficulty")
    }
    assert by_difficulty == {
        "(none)": (1, 0.0, 0.0),
        "moderate": (1, 0.0, 1.0),
        "simple": (1, 1.0, 1.0),
    }
    assert [g.name for g in comparison.by("db_id")] == ["superhero", "toxicology"]


def test_difference_counts_per_side() -> None:
    comparison = compare_runs(
        run(case("1", False), case("2", False)), run(case("1", False), case("2", True))
    )

    outputs = comparison.output_differences()
    structures = comparison.structure_differences()

    assert outputs == ({"empty_result": 2}, {"empty_result": 1})
    assert structures == ({"where_value": 2}, {"where_value": 1})


def test_csv_has_one_row_per_common_case_and_a_bom(tmp_path: Path) -> None:
    comparison = compare_runs(
        run(case("1", True), case("2", False)), run(case("1", False), case("2", True))
    )
    path = tmp_path / "out" / "flips.csv"

    write_csv(comparison, path)

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")  # Excel reads it as UTF-8
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert list(rows[0]) == list(CSV_COLUMNS)
    assert [(r["id"], r["change"], r["head_output_differences"]) for r in rows] == [
        ("1", "regressed", "empty_result"),
        ("2", "fixed", ""),
    ]
    assert rows[0]["question"] == "질문"


def test_csv_cells_that_start_like_a_formula_are_written_as_text(
    tmp_path: Path,
) -> None:
    hostile = case("1", False, pred_sql="@SUM(A1:A9)", question="+82 phone?")
    path = tmp_path / "flips.csv"

    write_csv(compare_runs(run(hostile), run(hostile)), path)

    with path.open(encoding="utf-8-sig", newline="") as file:
        (row,) = list(csv.DictReader(file))
    assert (row["base_pred_sql"], row["head_pred_sql"]) == ("'@SUM(A1:A9)",) * 2
    assert row["question"] == "'+82 phone?"
