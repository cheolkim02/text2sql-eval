import re
from dataclasses import replace
from pathlib import Path

import pytest

from text2sql_eval.execution.executor import QueryFailure
from text2sql_eval.facts import CaseDiff
from text2sql_eval.facts.output import OutputDiff
from text2sql_eval.facts.structure import Fact, StructureReport
from text2sql_eval.judge.ex import Correct, ExecError, Flag, Incorrect
from text2sql_eval.report.html_report import (
    build_page,
    render_html,
    sql_views,
    table_view,
    write_html_report,
)
from text2sql_eval.runfile import (
    CaseRecord,
    FileRef,
    ResultSample,
    Run,
    RunSettings,
    read_run,
)

EVIDENCE_RUN = (
    Path(__file__).resolve().parents[1]
    / "examples/results/gpt-4o-mini-evidence.run.json"
)

SAMPLE = ResultSample(columns=("name",), rows=(("Surtur",),), row_count=1)

CORRECT = CaseRecord(
    id="1",
    db_id="superhero",
    difficulty="simple",
    question="Who is the fire giant?",
    evidence="",
    gold_sql="SELECT name FROM superhero WHERE id = 1",
    pred_sql="SELECT name FROM superhero WHERE id = 1",
    prediction_state="given",
    verdict=Correct(),
    gold=SAMPLE,
    pred=SAMPLE,
)

WRONG = replace(
    CORRECT,
    id="2",
    difficulty="challenging",
    pred_sql="SELECT name, id FROM superhero WHERE id = 1",
    verdict=Incorrect(
        flags=(
            Flag("gold_rows_with_extra_columns", "extra columns"),
            Flag("tied_alternative_exists", "tied"),
        )
    ),
    pred=ResultSample(columns=("name", "id"), rows=(("Surtur", 1),), row_count=1),
    diff=CaseDiff(
        output=OutputDiff(
            ("column_mismatch",),
            gold_columns=1,
            pred_columns=2,
            gold_distinct_rows=1,
            pred_distinct_rows=1,
            gold_contained=True,
        ),
        structure=StructureReport(facts=(Fact("columns", "(none)", "id"),)),
    ),
)

FAILED = replace(
    CORRECT,
    id="3",
    db_id="toxicology",
    difficulty=None,
    pred_sql="SELEC name FROM",
    verdict=ExecError("pred", "error", 'near "SELEC": syntax error'),
    pred=QueryFailure("error", 'near "SELEC": syntax error'),
    diff=CaseDiff(
        output=OutputDiff(
            ("execution_failed",),
            gold_columns=1,
            pred_columns=0,
            gold_distinct_rows=1,
            pred_distinct_rows=0,
        ),
        structure=StructureReport((), parse_failed="pred"),
    ),
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
        settings=RunSettings(timeout_seconds=30.0, max_rows=None, allow_missing=False),
        meta={"model": "test-model"},
        cases=cases,
    )


@pytest.fixture(scope="module")
def evidence_run() -> Run:
    return read_run(EVIDENCE_RUN)


def test_report_of_the_committed_run_is_one_offline_page(evidence_run: Run) -> None:
    html = render_html(evidence_run, run_name="evidence.run.json")

    assert html.startswith("<!DOCTYPE html>")
    assert html.count('<details class="case"') == 432
    # Nothing is fetched: no linked files, images, imports or URLs.
    assert re.search(r"\b(?:src|href)\s*=", html) is None
    assert "<link" not in html
    assert "@import" not in html
    assert "url(" not in html
    # Wrong and failed cases are listed first by default (ADR 0039 plan).
    assert '<option value="wrong" selected>' in html


def test_committed_run_counts_match_the_published_results(evidence_run: Run) -> None:
    page = build_page(evidence_run, run_name="evidence.run.json")

    flags = {row.code: row.count for row in page.flag_counts}
    assert flags == {
        "empty_prediction_correct": 0,
        "gold_empty_correct": 0,
        "matches_tied_alternative_only": 5,
        "gold_rows_with_extra_columns": 25,
        "gold_columns_concatenated": 8,
        "tied_alternative_exists": 13,
    }
    suspect = [c for c in page.cases if "suspect_incorrect" in c.filters["flag"]]
    assert len(suspect) == 38  # examples/results/README.md
    wrong = [c for c in page.cases if "wrong" in c.filters["status"].split()]
    assert len(wrong) == 165


def test_user_text_is_escaped_everywhere() -> None:
    hostile = replace(
        WRONG,
        db_id='super"hero',
        question='<script>alert("q")</script>',
        evidence="</p><b>bold</b>",
        gold_sql="SELECT '<i>' FROM t",
        gold=ResultSample(
            columns=("<th>",), rows=(("<img src=x onerror=alert(1)>",),), row_count=1
        ),
    )

    html = render_html(make_run(hostile), run_name="<run>.json")

    for raw in (
        '<script>alert("q")</script>',
        "<b>bold</b>",
        "'<i>'",
        "<img src=x",
        "<th><th>",
        "<run>",
        'data-db="super"hero"',
    ):
        assert raw not in html
    assert "&lt;script&gt;alert(&#34;q&#34;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "<th>&lt;th&gt;</th>" in html
    assert 'data-db="super&#34;hero"' in html
    assert html.count("<script>") == 1  # only the page's own filter script


def test_sql_is_formatted_one_clause_per_line_and_the_original_kept() -> None:
    gold, pred = sql_views(
        "select name from superhero where id = 1;",
        "SELECT T.name FROM superhero AS T WHERE T.id = 2",
        highlight=True,
    )

    assert gold.formatted
    assert [(b.text, b.differs) for b in gold.blocks] == [
        ("SELECT\n  name", False),
        ("FROM superhero", False),
        ("WHERE\n  id = 1", True),
    ]
    assert [b.differs for b in pred.blocks] == [False, False, True]
    assert gold.original == "select name from superhero where id = 1;"


def test_nothing_is_highlighted_without_the_highlight_option() -> None:
    gold, pred = sql_views("SELECT 1", "SELECT 2", highlight=False)

    assert not any(b.differs for b in (*gold.blocks, *pred.blocks))


def test_unparsable_or_missing_sql_is_shown_as_written_and_not_marked() -> None:
    gold, pred = sql_views("SELECT name FROM t", "SELEC name FROM", highlight=True)

    assert [(b.text, b.differs) for b in pred.blocks] == [("SELEC name FROM", False)]
    assert not pred.formatted
    assert not any(b.differs for b in gold.blocks)
    _, missing = sql_views("SELECT 1", "   ", highlight=True)
    assert missing.blocks == ()


def test_rows_missing_from_the_other_complete_result_are_marked() -> None:
    page = build_page(
        make_run(
            replace(
                WRONG,
                pred=ResultSample(
                    columns=("name",), rows=(("Surtur",), ("Ymir",)), row_count=2
                ),
            )
        ),
        run_name="r.json",
    )

    (case,) = page.cases
    assert [row.differs for row in case.gold_result.rows] == [False]
    assert [row.differs for row in case.pred_result.rows] == [False, True]


def test_result_tables_note_samples_failures_and_special_values() -> None:
    long = ResultSample(
        columns=("a", "b", "c"),
        rows=((None, b"\x00\xff", 1.5),) * 20,
        row_count=153,
    )

    view = table_view(long)

    assert view.caption == "앞 20행 / 전체 153행"
    cells = view.rows[0].cells
    assert (cells[0].text, cells[0].null) == ("NULL", True)
    assert cells[1].text == "x'00ff' (2 bytes)"
    assert cells[2].text == "1.5"
    failed = table_view(QueryFailure("timeout", "did not finish within 30 s"))
    assert failed.failure == "timeout: did not finish within 30 s"
    assert table_view(SAMPLE).caption == "1행"


def test_case_views_carry_differences_flags_and_filter_tokens() -> None:
    page = build_page(make_run(CORRECT, WRONG, FAILED), run_name="r.json")

    correct, wrong, failed = page.cases
    assert correct.filters["status"] == "correct"
    assert correct.outputs == correct.facts == correct.flags == ()
    assert wrong.filters["status"] == "incorrect wrong"
    assert set(wrong.filters["flag"].split()) == {
        "gold_rows_with_extra_columns",
        "suspect_incorrect",
        "tied_alternative_exists",
        "info",
    }
    assert [(n.label, n.gold, n.pred) for n in wrong.numbers] == [
        ("컬럼 수", 1, 2),
        ("서로 다른 행 수", 1, 1),
    ]
    assert [(f.code, f.gold, f.pred) for f in wrong.facts] == [
        ("columns", "(none)", "id")
    ]
    assert failed.filters["difficulty"] == "none"
    assert failed.error == '예측 SQL 실행 실패 (error): near "SELEC": syntax error'
    assert failed.structure_note.startswith("예측 SQL을 파싱하지 못해")


def test_summary_groups_and_counts() -> None:
    page = build_page(make_run(CORRECT, WRONG, FAILED), run_name="r.json")

    assert [(r.label, r.count) for r in page.status_counts] == [
        ("전체", 3),
        ("정답", 1),
        ("오답", 1),
        ("오류", 1),
    ]
    assert [(g.name, g.cases, g.ex) for g in page.by_difficulty] == [
        ("simple", 1, "100.0%"),
        ("challenging", 1, "0.0%"),
        ("(없음)", 1, "0.0%"),
    ]
    # Most frequent first; kinds that never occur stay listed with 0.
    assert [(r.code, r.count) for r in page.output_counts][:2] == [
        ("execution_failed", 1),
        ("column_mismatch", 1),
    ]
    assert page.output_counts[-1].count == 0
    assert ("meta: model", "test-model") in page.info


def test_write_html_creates_parent_folders(tmp_path: Path) -> None:
    path = tmp_path / "out" / "report.html"

    write_html_report(make_run(CORRECT), path, run_name="r.json")

    assert "<title>text2sql-eval report: r.json</title>" in path.read_text(
        encoding="utf-8"
    )
