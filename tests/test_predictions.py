import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from text2sql_eval.datasets.bird import Case, Dataset
from text2sql_eval.datasets.predictions import (
    Prediction,
    load_jsonl_predictions,
    load_text_predictions,
)
from text2sql_eval.errors import InputError


def _dataset(*ids: str) -> Dataset:
    cases = tuple(
        Case(
            id=case_id,
            db_id="superhero",
            question=f"question {case_id}",
            evidence="",
            gold_sql="SELECT 1",
            difficulty=None,
        )
        for case_id in ids
    )
    return Dataset(path=Path("dev.json"), cases=cases)


DATASET = _dataset("10", "11", "12")


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _jsonl(*rows: object) -> str:
    return "".join(json.dumps(row) + "\n" for row in rows)


# --- text format -----------------------------------------------------------


def test_text_lines_map_to_cases_in_dataset_order(tmp_path: Path) -> None:
    path = _write(tmp_path, "p.txt", "SELECT 10\n  SELECT 11  \nSELECT 12\n")

    preds = load_text_predictions(path, DATASET)

    assert preds == {
        "10": Prediction("10", "SELECT 10"),
        "11": Prediction("11", "SELECT 11"),
        "12": Prediction("12", "SELECT 12"),
    }


def test_text_empty_line_is_an_empty_prediction(tmp_path: Path) -> None:
    path = _write(tmp_path, "p.txt", "SELECT 10\n\nSELECT 12")

    preds = load_text_predictions(path, DATASET)

    assert preds["11"].sql == ""
    assert preds["12"].sql == "SELECT 12"


@pytest.mark.parametrize("loader", [load_text_predictions, load_jsonl_predictions])
def test_ignores_a_leading_byte_order_mark(tmp_path: Path, loader: object) -> None:
    # Windows editors and Excel save UTF-8 with a BOM; it must not reach the SQL.
    if loader is load_text_predictions:
        path = tmp_path / "p.txt"
        path.write_text("SELECT 10\nSELECT 11\nSELECT 12\n", encoding="utf-8-sig")
        preds = load_text_predictions(path, DATASET)
    else:
        path = tmp_path / "p.jsonl"
        rows = _jsonl(*({"id": i, "sql": f"SELECT {i}"} for i in (10, 11, 12)))
        path.write_text(rows, encoding="utf-8-sig")
        preds = load_jsonl_predictions(path, DATASET)

    assert preds["10"].sql == "SELECT 10"


def test_text_accepts_windows_line_endings(tmp_path: Path) -> None:
    path = _write(tmp_path, "p.txt", "SELECT 10\r\nSELECT 11\r\nSELECT 12\r\n")

    assert load_text_predictions(path, DATASET)["11"].sql == "SELECT 11"


@pytest.mark.parametrize(
    "text", ["SELECT 10\nSELECT 11\n", "a\nb\nc\nd\n", "a\nb\nc\n\n"]
)
def test_text_rejects_a_line_count_that_differs_from_the_dataset(
    tmp_path: Path, text: str
) -> None:
    with pytest.raises(InputError) as excinfo:
        load_text_predictions(_write(tmp_path, "p.txt", text), DATASET)

    message = str(excinfo.value)
    assert "lines but the dataset dev.json has 3 cases" in message
    assert "keep an empty line where the model produced no SQL" in message


@given(
    st.lists(
        st.text(st.characters(codec="utf-8", exclude_characters="\n\r")).map(str.strip),
        min_size=1,
        max_size=20,
    )
)
def test_text_round_trips_any_single_line_sql(sqls: list[str]) -> None:
    # Unicode line separators such as U+2028 must not split a prediction.
    dataset = _dataset(*(str(i) for i in range(len(sqls))))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "p.txt"
        path.write_text("\n".join(sqls) + "\n", encoding="utf-8")

        preds = load_text_predictions(path, dataset)

    assert [preds[case.id].sql for case in dataset.cases] == sqls


# --- JSONL format ----------------------------------------------------------


def test_jsonl_matches_integer_and_string_ids_and_keeps_meta(tmp_path: Path) -> None:
    text = _jsonl(
        {"id": 12, "sql": "SELECT 12"},
        {"id": "10", "sql": " SELECT 10 ", "meta": {"latency_ms": 1830}},
        {"id": 11, "sql": ""},
    )

    preds = load_jsonl_predictions(_write(tmp_path, "p.jsonl", text), DATASET)

    assert preds["10"] == Prediction("10", "SELECT 10", {"latency_ms": 1830})
    assert preds["11"].sql == ""
    assert preds["12"].meta == {}


def test_jsonl_skips_blank_lines(tmp_path: Path) -> None:
    text = (
        "\n"
        + _jsonl({"id": 10, "sql": "a"})
        + "\n"
        + _jsonl({"id": 11, "sql": "b"}, {"id": 12, "sql": "c"})
    )

    preds = load_jsonl_predictions(_write(tmp_path, "p.jsonl", text), DATASET)

    assert sorted(preds) == ["10", "11", "12"]


def test_jsonl_missing_cases_are_an_error_that_lists_them(tmp_path: Path) -> None:
    dataset = _dataset(*(str(i) for i in range(10)))
    path = _write(tmp_path, "p.jsonl", _jsonl({"id": 0, "sql": "a"}))

    with pytest.raises(InputError) as excinfo:
        load_jsonl_predictions(path, dataset)

    message = str(excinfo.value)
    assert "9 of 10 cases have no prediction: 1, 2, 3, 4, 5 and 4 more" in message
    assert "allow missing predictions" in message


def test_jsonl_allow_missing_returns_only_given_cases(tmp_path: Path) -> None:
    path = _write(tmp_path, "p.jsonl", _jsonl({"id": 11, "sql": "b"}))

    preds = load_jsonl_predictions(path, DATASET, allow_missing=True)

    assert list(preds) == ["11"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            _jsonl({"id": 99, "sql": "a"}),
            "line 1: id 99 is not in the dataset dev.json",
        ),
        (
            _jsonl({"id": 10, "sql": "a"}, {"id": "10", "sql": "b"}),
            "line 2: id 10 appears twice (first on line 1)",
        ),
        ('{"id": 10, "sql": "a",}\n', "line 1: invalid JSON at column"),
        ('[10, "a"]\n', "line 1: expected a JSON object, found array"),
        (_jsonl({"sql": "a"}), "line 1: missing field 'id'"),
        (_jsonl({"id": 10}), "line 1: missing field 'sql'"),
        (
            _jsonl({"id": True, "sql": "a"}),
            "'id' must be an integer or a non-empty string",
        ),
        (
            _jsonl({"id": "", "sql": "a"}),
            "'id' must be an integer or a non-empty string",
        ),
        (_jsonl({"id": 1.5, "sql": "a"}), "found number"),
        (_jsonl({"id": 10, "sql": None}), "'sql' must be a string, found null"),
        (
            _jsonl({"id": 10, "sql": "a", "meta": [1]}),
            "'meta' must be an object, found array",
        ),
    ],
)
def test_jsonl_rejects_bad_lines_with_their_line_number(
    tmp_path: Path, text: str, expected: str
) -> None:
    with pytest.raises(InputError) as excinfo:
        load_jsonl_predictions(_write(tmp_path, "p.jsonl", text), DATASET)

    assert expected in str(excinfo.value)
