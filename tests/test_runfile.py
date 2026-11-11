import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from text2sql_eval.errors import InputError
from text2sql_eval.execution.executor import QueryFailure
from text2sql_eval.facts import CaseDiff
from text2sql_eval.facts.output import OutputDiff
from text2sql_eval.facts.structure import Fact, StructureReport
from text2sql_eval.judge.ex import Correct, ExecError, Flag, Incorrect
from text2sql_eval.runfile import (
    CaseRecord,
    FileRef,
    ResultSample,
    Run,
    RunSettings,
    read_run,
    sha256_of,
    write_run,
)

BASE = CaseRecord(
    id="1",
    db_id="superhero",
    difficulty="simple",
    question="How many heroes?",
    evidence="",
    gold_sql="SELECT COUNT(*) FROM superhero",
    pred_sql="SELECT COUNT(id) FROM superhero",
    prediction_state="given",
    verdict=Correct(),
    gold=ResultSample(columns=("COUNT(*)",), rows=((750,),), row_count=1),
    pred=ResultSample(columns=("COUNT(id)",), rows=((750,),), row_count=1),
)


def _run(*cases: CaseRecord) -> Run:
    return Run(
        tool_version="0.1.0",
        created_at="2026-11-09T01:02:03Z",
        dataset=FileRef("dev.json", "a" * 64),
        predictions=FileRef("preds.jsonl", "b" * 64),
        prediction_format="jsonl",
        tied=FileRef("dev_tied_append.json", "c" * 64),
        db_dir="dev_databases",
        settings=RunSettings(timeout_seconds=30.0, max_rows=None, allow_missing=True),
        meta={"model": "test-model", "prompt": "v3"},
        cases=cases,
    )


RUN = _run(
    BASE,
    replace(
        BASE,
        id="2",
        verdict=Incorrect(
            flags=(
                Flag("tied_alternative_exists", "has an alternative"),
                Flag("matches_tied_alternative_only", "matches only the alternative"),
            )
        ),
        pred=ResultSample(
            columns=("blob", "big", "nothing", "real"),
            rows=((b"\x00\xff", float("inf"), None, 1.5),),
            row_count=7,
        ),
        pred_meta={"latency_ms": 1830, "tokens": [1, 2]},
        diff=CaseDiff(
            output=OutputDiff(
                ("column_mismatch", "row_count_differs"),
                gold_columns=1,
                pred_columns=4,
                gold_distinct_rows=41,
                pred_distinct_rows=7,
                gold_contained=False,
            ),
            structure=StructureReport(
                facts=(Fact("where_value", "a = 'X'", "a = 'x'"),)
            ),
        ),
    ),
    replace(
        BASE,
        id="3",
        prediction_state="missing",
        pred_sql="",
        verdict=ExecError("pred", "timeout", "did not finish within 30 s"),
        pred=QueryFailure("timeout", "did not finish within 30 s"),
        diff=CaseDiff(
            output=OutputDiff(
                ("execution_failed",),
                gold_columns=1,
                pred_columns=0,
                gold_distinct_rows=1,
                pred_distinct_rows=0,
            ),
            structure=StructureReport(facts=(), parse_failed="pred"),
        ),
    ),
)


def test_round_trips_every_field(tmp_path: Path) -> None:
    path = tmp_path / "runs" / "run.json"

    write_run(RUN, path)

    assert read_run(path) == RUN


def test_writes_a_summary_and_standard_json(tmp_path: Path) -> None:
    path = tmp_path / "run.json"

    write_run(RUN, path)

    text = path.read_text(encoding="utf-8")
    assert "Infinity" not in text and "NaN" not in text
    document = json.loads(text)
    assert document["schema_version"] == 3
    assert document["summary"] == {
        "total": 3,
        "correct": 1,
        "incorrect": 1,
        "error": 1,
        "ex": 1 / 3,
    }
    assert document["cases"][1]["pred"]["rows"] == [
        [{"$bytes": "00ff"}, {"$float": "inf"}, None, 1.5]
    ]


def test_ex_of_an_empty_run_is_zero() -> None:
    assert _run().summary.ex == 0.0


def test_rejects_another_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    write_run(RUN, path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["schema_version"] = 99
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(InputError, match="schema_version is 99, but this tool reads 3"):
        read_run(path)


@pytest.mark.parametrize(
    ("keys", "value", "expected"),
    [
        (("cases", 0, "status"), "maybe", "cases[0].status must be one of"),
        (("cases", 0, "question"), None, "cases[0].question must be a string"),
        (("settings", "max_rows"), "10", "settings.max_rows must be an integer"),
        (("cases", 1, "pred", "rows", 0, 0), [1], "cases[1].pred.rows[0] must be"),
        (
            ("cases", 1, "diff", "output", "differences", 0),
            "typo",
            "cases[1].diff.output.differences[0] must be one of",
        ),
        (
            ("cases", 1, "diff", "sql_structure", "differences", 0, "kind"),
            "typo",
            "cases[1].diff.sql_structure.differences[0].kind must be one of",
        ),
    ],
)
def test_reports_where_a_damaged_file_is_wrong(
    tmp_path: Path, keys: tuple[str | int, ...], value: object, expected: str
) -> None:
    path = tmp_path / "run.json"
    write_run(RUN, path)
    document: Any = json.loads(path.read_text(encoding="utf-8"))
    target = document
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(InputError) as excinfo:
        read_run(path)

    assert expected in str(excinfo.value)


def test_sha256_of_a_file(tmp_path: Path) -> None:
    path = tmp_path / "x.txt"
    path.write_bytes(b"abc")

    assert sha256_of(path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
