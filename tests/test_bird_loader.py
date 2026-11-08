import json
from pathlib import Path

import pytest

from text2sql_eval.datasets.bird import Case, load_bird, load_bird_tied
from text2sql_eval.errors import InputError

BIRD_MINI_DEV = Path(__file__).resolve().parents[1] / "examples/bird-mini/dev.json"


def _question(question_id: object = 1, **overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "question_id": question_id,
        "db_id": "superhero",
        "question": "How many heroes are there?",
        "evidence": "",
        "SQL": "SELECT COUNT(*) FROM superhero",
        "difficulty": "simple",
    }
    item.update(overrides)
    return item


def _write(tmp_path: Path, content: object) -> Path:
    path = tmp_path / "dev.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


def test_loads_the_committed_bird_subset() -> None:
    dataset = load_bird(BIRD_MINI_DEV)

    assert len(dataset.cases) == 432
    assert len(set(dataset.ids)) == 432
    assert {case.db_id for case in dataset.cases} == {
        "superhero",
        "student_club",
        "toxicology",
    }
    assert {case.difficulty for case in dataset.cases} == {
        "simple",
        "moderate",
        "challenging",
    }


def test_converts_question_id_to_string_and_keeps_file_order(tmp_path: Path) -> None:
    path = _write(tmp_path, [_question(7), _question(3, difficulty=None)])

    dataset = load_bird(path)

    assert dataset.ids == ("7", "3")
    assert dataset.cases[1] == Case(
        id="3",
        db_id="superhero",
        question="How many heroes are there?",
        evidence="",
        gold_sql="SELECT COUNT(*) FROM superhero",
        difficulty=None,
    )


def test_difficulty_may_be_absent(tmp_path: Path) -> None:
    item = _question()
    del item["difficulty"]

    assert load_bird(_write(tmp_path, [item])).cases[0].difficulty is None


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ({"question_id": 1}, "expected a JSON array of question objects"),
        ([1], "item 0: expected a question object, found number"),
        ([_question(), "x"], "item 1: expected a question object, found string"),
        ([_question("1")], "field 'question_id' must be an integer, found string"),
        ([_question(True)], "field 'question_id' must be an integer, found boolean"),
        ([_question(SQL=None)], "field 'SQL' must be a string, found null"),
        (
            [_question(difficulty=3)],
            "field 'difficulty' must be a string, found number",
        ),
        ([_question(1), _question(1)], "question_id 1 is repeated (first at item 0)"),
    ],
)
def test_rejects_malformed_questions(
    tmp_path: Path, content: object, expected: str
) -> None:
    with pytest.raises(InputError) as excinfo:
        load_bird(_write(tmp_path, content))

    assert expected in str(excinfo.value)


def test_reports_the_missing_field_and_how_to_fix_it(tmp_path: Path) -> None:
    item = _question()
    del item["SQL"]

    with pytest.raises(InputError) as excinfo:
        load_bird(_write(tmp_path, [item]))

    message = str(excinfo.value)
    assert "item 0: missing field 'SQL'" in message
    assert "hint: add 'SQL' to every question object" in message


def test_reports_invalid_json_with_its_position(tmp_path: Path) -> None:
    path = tmp_path / "dev.json"
    path.write_text('[\n  {"question_id": 1,}\n]', encoding="utf-8")

    with pytest.raises(InputError) as excinfo:
        load_bird(path)

    # The column for the same error differs across Python versions; check the line.
    assert "line 2: invalid JSON at column" in str(excinfo.value)


def test_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="file not found"):
        load_bird(tmp_path / "nope.json")


def test_reports_non_utf8_files(tmp_path: Path) -> None:
    path = tmp_path / "dev.json"
    path.write_bytes(b"[\xff]")

    with pytest.raises(InputError, match="not valid UTF-8"):
        load_bird(path)


# --- tied-rows alternative gold --------------------------------------------


def test_loads_the_committed_tied_alternatives() -> None:
    dataset = load_bird(BIRD_MINI_DEV)

    tied = load_bird_tied(BIRD_MINI_DEV.with_name("dev_tied_append.json"), dataset)

    assert len(tied) == 13
    assert set(tied) <= set(dataset.ids)
    assert "LIMIT 1" in next(c.gold_sql for c in dataset.cases if c.id == "810")
    assert "LIMIT 1" not in tied["810"]


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (_question(99), "question_id 99 is not in the dataset"),
        (
            _question(1, db_id="toxicology"),
            (
                "question_id 1 is for database 'toxicology', but the dataset has it "
                "for 'superhero'"
            ),
        ),
    ],
)
def test_rejects_tied_entries_that_do_not_match_the_dataset(
    tmp_path: Path, entry: dict[str, object], expected: str
) -> None:
    dataset = load_bird(_write(tmp_path, [_question(1)]))
    tied_path = tmp_path / "tied.json"
    tied_path.write_text(json.dumps([entry]), encoding="utf-8")

    with pytest.raises(InputError) as excinfo:
        load_bird_tied(tied_path, dataset)

    assert expected in str(excinfo.value)
