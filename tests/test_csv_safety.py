import pytest
from hypothesis import given
from hypothesis import strategies as st

from text2sql_eval.csv_safety import FORMULA_STARTS, excel_safe


@pytest.mark.parametrize(
    "first", ["=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠"]
)
def test_cells_starting_like_a_formula_get_an_apostrophe(first: str) -> None:
    assert excel_safe(first + "1+1") == "'" + first + "1+1"


@pytest.mark.parametrize(
    "cell",
    [
        "",
        "SELECT name FROM hero WHERE id = 1",
        "195",
        "불의 거인은 누구인가?",
        " =1",  # a space is not in OWASP's list of first characters
        "'=1",  # already starts with an apostrophe
    ],
)
def test_other_cells_are_unchanged(cell: str) -> None:
    assert excel_safe(cell) == cell


@given(st.text())
def test_result_never_starts_like_a_formula_and_keeps_the_text(cell: str) -> None:
    safe = excel_safe(cell)

    assert safe in (cell, "'" + cell)
    assert not safe or safe[0] not in FORMULA_STARTS
