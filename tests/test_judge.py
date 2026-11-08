from collections import Counter
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from text2sql_eval.datasets.bird import load_bird, load_bird_tied
from text2sql_eval.execution.executor import (
    Query,
    QueryFailure,
    Rows,
    SqlValue,
    execute_all,
)
from text2sql_eval.judge.ex import (
    Correct,
    ExecError,
    Incorrect,
    Verdict,
    judge_case,
    status_of,
)

BIRD_MINI = Path(__file__).resolve().parents[1] / "examples/bird-mini"


def rows(*values: tuple[SqlValue, ...], columns: tuple[str, ...] = ("c",)) -> Rows:
    return Rows(columns=columns, rows=values)


def flag_kinds(verdict: Verdict) -> list[str]:
    return [flag.kind for flag in verdict.flags]


# --- the official rule -----------------------------------------------------


def test_row_order_and_duplicates_are_ignored() -> None:
    verdict = judge_case(rows((1,), (2,)), rows((2,), (1,), (1,)), pred_is_empty=False)

    assert verdict == Correct()


def test_value_order_inside_a_row_matters() -> None:
    gold = rows(("Ana", 1.7), columns=("name", "height"))
    pred = rows((1.7, "Ana"), columns=("height", "name"))

    assert judge_case(gold, pred, pred_is_empty=False) == Incorrect()


def test_column_names_are_ignored() -> None:
    gold = rows((3,), columns=("COUNT(*)",))
    pred = rows((3,), columns=("n",))

    assert judge_case(gold, pred, pred_is_empty=False) == Correct()


def test_values_compare_with_python_equality() -> None:
    # 1 == 1.0 in Python, so the official script treats them as equal.
    assert judge_case(rows((1,)), rows((1.0,)), pred_is_empty=False) == Correct()
    assert judge_case(rows((0.3,)), rows((0.1 + 0.2,)), pred_is_empty=False) == (
        Incorrect()
    )


SQL_VALUES = st.sampled_from([0, 1, 1.0, 2, 0.5, "a", "b", "", b"a", None])


def row_lists(arity: int) -> st.SearchStrategy[list[tuple[SqlValue, ...]]]:
    return st.lists(st.tuples(*[SQL_VALUES] * arity), max_size=6)


@given(st.data())
def test_agrees_with_the_official_comparison(data: st.DataObject) -> None:
    arity = data.draw(st.integers(min_value=1, max_value=3))
    gold_rows = data.draw(row_lists(arity))
    pred_rows = data.draw(row_lists(data.draw(st.sampled_from([arity, arity + 1]))))

    verdict = judge_case(
        Rows(columns=("g",) * arity, rows=tuple(gold_rows)),
        Rows(columns=("p",), rows=tuple(pred_rows)),
        pred_is_empty=False,
    )

    # BIRD's evaluation.py: `if set(predicted_res) == set(ground_truth_res): res = 1`
    official = set(pred_rows) == set(gold_rows)
    assert isinstance(verdict, Correct) is official
    assert isinstance(verdict, Incorrect) is not official


# --- failures --------------------------------------------------------------


def test_a_failed_prediction_is_an_error_on_the_prediction_side() -> None:
    verdict = judge_case(
        rows((1,)), QueryFailure("error", "no such column: x"), pred_is_empty=False
    )

    assert verdict == ExecError("pred", "error", "no such column: x")


def test_a_failed_gold_query_is_an_error_on_the_gold_side() -> None:
    verdict = judge_case(
        QueryFailure("timeout", "did not finish within 30 s"),
        rows((1,)),
        pred_is_empty=False,
    )

    assert verdict == ExecError("gold", "timeout", "did not finish within 30 s")


def test_when_both_fail_the_prediction_is_reported() -> None:
    verdict = judge_case(
        QueryFailure("error", "gold broke"),
        QueryFailure("row_limit", "more than 10 rows"),
        pred_is_empty=False,
    )

    assert verdict == ExecError("pred", "row_limit", "more than 10 rows")


# --- flags -----------------------------------------------------------------


def test_empty_prediction_judged_correct_is_flagged() -> None:
    verdict = judge_case(rows(), Rows(columns=(), rows=()), pred_is_empty=True)

    assert isinstance(verdict, Correct)
    assert flag_kinds(verdict) == ["empty_prediction_correct"]


def test_empty_prediction_against_a_non_empty_gold_is_just_incorrect() -> None:
    verdict = judge_case(rows((1,)), Rows(columns=(), rows=()), pred_is_empty=True)

    assert verdict == Incorrect()


def test_tied_alternative_is_noted_even_when_correct() -> None:
    verdict = judge_case(
        rows(("Ana",)),
        rows(("Ana",)),
        pred_is_empty=False,
        tied=rows(("Ana",), ("Bo",)),
    )

    assert isinstance(verdict, Correct)
    assert flag_kinds(verdict) == ["tied_alternative_exists"]


def test_matching_only_the_tied_alternative_is_flagged_but_stays_incorrect() -> None:
    verdict = judge_case(
        rows(("Ana",)),
        rows(("Bo",), ("Ana",)),
        pred_is_empty=False,
        tied=rows(("Ana",), ("Bo",)),
    )

    assert isinstance(verdict, Incorrect)
    assert flag_kinds(verdict) == [
        "tied_alternative_exists",
        "matches_tied_alternative_only",
    ]


def test_a_failed_tied_query_only_leaves_the_exists_flag() -> None:
    verdict = judge_case(
        rows(("Ana",)),
        rows(("Bo",)),
        pred_is_empty=False,
        tied=QueryFailure("error", "broken alternative"),
    )

    assert isinstance(verdict, Incorrect)
    assert flag_kinds(verdict) == ["tied_alternative_exists"]


@pytest.mark.parametrize(
    ("verdict", "status"),
    [
        (Correct(), "correct"),
        (Incorrect(), "incorrect"),
        (ExecError("pred", "error", "x"), "error"),
    ],
)
def test_status_names(verdict: Verdict, status: str) -> None:
    assert status_of(verdict) == status


# --- the committed BIRD subset ---------------------------------------------


def _db(db_id: str) -> Path:
    return BIRD_MINI / "dev_databases" / db_id / f"{db_id}.sqlite"


def test_every_gold_query_is_correct_against_itself() -> None:
    dataset = load_bird(BIRD_MINI / "dev.json")
    results = execute_all([Query(_db(c.db_id), c.gold_sql) for c in dataset.cases])

    verdicts = [judge_case(r, r, pred_is_empty=False) for r in results]

    assert Counter(status_of(v) for v in verdicts) == {"correct": 432}


def test_tied_alternatives_as_predictions_are_flagged() -> None:
    # 11 of the 13 alternatives return different rows from the original gold
    # (examples/bird-mini/SOURCE.md); those must be flagged, not counted correct.
    dataset = load_bird(BIRD_MINI / "dev.json")
    tied = load_bird_tied(BIRD_MINI / "dev_tied_append.json", dataset)
    cases = [case for case in dataset.cases if case.id in tied]
    gold = execute_all([Query(_db(c.db_id), c.gold_sql) for c in cases])
    alternative = execute_all([Query(_db(c.db_id), tied[c.id]) for c in cases])

    verdicts = [
        judge_case(g, a, pred_is_empty=False, tied=a)
        for g, a in zip(gold, alternative, strict=True)
    ]

    assert Counter(status_of(v) for v in verdicts) == {"incorrect": 11, "correct": 2}
    assert all(
        "matches_tied_alternative_only" in flag_kinds(v)
        for v in verdicts
        if isinstance(v, Incorrect)
    )
