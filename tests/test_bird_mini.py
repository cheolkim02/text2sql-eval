"""Guard the committed BIRD subset against accidental changes (see SOURCE.md)."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

BIRD_MINI = Path(__file__).resolve().parents[1] / "examples" / "bird-mini"

EXPECTED_QUESTIONS = {"superhero": 129, "student_club": 158, "toxicology": 145}
EXPECTED_SHA256 = {
    "superhero": "75e94a2c3236ee3bb2c01fb97a1c4b4c1c269bcefd4eab1d04be323d2d0825b1",
    "student_club": "eb89bcfe97eefa386a27904ec5aa15159811a7eac894ec659a36e48fa9f76b77",
    "toxicology": "f5fa7f21af1ad878ff8fef1b0582b8cb2d7ed63dbac65ff16d2ba05667650c5b",
}


def _load(name: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = json.loads(
        (BIRD_MINI / name).read_text(encoding="utf-8")
    )
    return rows


def test_question_counts_per_database() -> None:
    counts = Counter(str(row["db_id"]) for row in _load("dev.json"))
    assert counts == EXPECTED_QUESTIONS


def test_question_ids_are_unique() -> None:
    ids = [row["question_id"] for row in _load("dev.json")]
    assert len(ids) == len(set(ids))


def test_tied_alternatives_refer_to_known_questions() -> None:
    known = {row["question_id"] for row in _load("dev.json")}
    tied = _load("dev_tied_append.json")
    assert len(tied) == 13
    assert {row["question_id"] for row in tied} <= known


@pytest.mark.parametrize("db_id", sorted(EXPECTED_SHA256))
def test_database_file_matches_recorded_checksum(db_id: str) -> None:
    path = BIRD_MINI / "dev_databases" / db_id / f"{db_id}.sqlite"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_SHA256[db_id]
