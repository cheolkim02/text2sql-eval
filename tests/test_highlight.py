import pytest
from sqlglot.expressions.core import Expr

from text2sql_eval.execution.executor import QueryFailure, SqlValue
from text2sql_eval.facts.structure import parse
from text2sql_eval.report.highlight import (
    clause_blocks,
    differing_clauses,
    differing_rows,
)
from text2sql_eval.runfile import ResultSample


def parsed(sql: str) -> Expr:
    tree = parse(sql)
    assert tree is not None
    return tree


@pytest.mark.parametrize(
    ("gold", "pred", "expected"),
    [
        # Normalization: aliases, qualifiers, identifier case, output names.
        (
            "SELECT T1.name FROM superhero AS T1 WHERE T1.id = 1",
            "SELECT s.Name FROM SuperHero s WHERE id = 1",
            set[str](),
        ),
        ("SELECT COUNT(id) AS n FROM t", "SELECT COUNT(id) FROM t", set[str]()),
        # A string literal keeps its case, as in the where_value difference.
        (
            "SELECT id FROM t WHERE power = 'Fly'",
            "SELECT id FROM t WHERE power = 'fly'",
            {"where"},
        ),
        ("SELECT DISTINCT a FROM t", "SELECT a FROM t", {"select"}),
        (
            "SELECT a FROM t JOIN u ON t.id = u.id",
            "SELECT a FROM t",
            {"from"},
        ),
        (
            "SELECT a FROM t ORDER BY a DESC LIMIT 1",
            "SELECT a FROM t",
            {"order", "limit"},
        ),
        ("SELECT a FROM t LIMIT 1 OFFSET 1", "SELECT a FROM t LIMIT 1", {"limit"}),
        (
            "SELECT a, COUNT(*) FROM t GROUP BY a HAVING COUNT(*) > 1",
            "SELECT a, COUNT(*) FROM t GROUP BY a",
            {"having"},
        ),
        # A subquery belongs to the clause it sits in.
        (
            "SELECT a FROM t WHERE id IN (SELECT id FROM u WHERE x = 1)",
            "SELECT a FROM t WHERE id IN (SELECT id FROM u WHERE x = 2)",
            {"where"},
        ),
        # Writing order SQLite ignores: inner join order, INNER, = sides, AND.
        (
            "SELECT a FROM atom AS T1 INNER JOIN bond AS T2 ON T1.mid = T2.mid",
            "SELECT a FROM bond JOIN atom ON bond.mid = atom.mid",
            set[str](),
        ),
        (
            "SELECT id FROM t WHERE bond_type = '#' AND molecule_id = 'TR041'",
            "SELECT id FROM t WHERE (molecule_id = 'TR041') AND bond_type = '#'",
            set[str](),
        ),
        (
            "SELECT a FROM t WHERE x = 1 AND y = 2",
            "SELECT a FROM t WHERE x = 1 OR y = 2",
            {"where"},
        ),
        # Outer joins and different join conditions are real differences.
        (
            "SELECT a FROM t JOIN u ON t.id = u.id",
            "SELECT a FROM t LEFT JOIN u ON t.id = u.id",
            {"from"},
        ),
        (
            "SELECT a FROM atom JOIN connected ON atom.atom_id = connected.atom_id",
            "SELECT a FROM atom JOIN connected ON atom.atom_id = connected.atom_id2",
            {"from"},
        ),
        # Not a plain SELECT on one side: clauses cannot be lined up.
        ("SELECT a FROM t UNION SELECT a FROM u", "SELECT a FROM t", set[str]()),
    ],
)
def test_differing_clauses(gold: str, pred: str, expected: set[str]) -> None:
    assert differing_clauses(parsed(gold), parsed(pred)) == expected


def test_clause_blocks_follow_the_outer_clauses_of_pretty_sql() -> None:
    sql = (
        "WITH a AS (SELECT 1 AS x) SELECT T.x FROM a AS T "
        "LEFT JOIN b ON T.x = b.x CROSS JOIN c WHERE T.x IN (SELECT x FROM d) "
        "GROUP BY T.x HAVING COUNT(*) > 1 ORDER BY T.x LIMIT 3 OFFSET 2"
    )
    pretty = parsed(sql).sql(dialect="sqlite", pretty=True)

    blocks = clause_blocks(pretty)

    assert [clause for clause, _ in blocks] == [
        "with",
        "select",
        "from",
        "where",
        "group",
        "having",
        "order",
        "limit",
    ]
    assert "\n".join(text for _, text in blocks) == pretty  # nothing lost
    assert blocks[2][1] == ("FROM a AS T\nLEFT JOIN b\n  ON T.x = b.x\nCROSS JOIN c")


def sample(*rows: tuple[SqlValue, ...], total: int | None = None) -> ResultSample:
    width = len(rows[0]) if rows else 1
    return ResultSample(
        columns=tuple(f"c{i}" for i in range(width)),
        rows=rows,
        row_count=len(rows) if total is None else total,
    )


def test_rows_missing_from_the_other_side_are_marked() -> None:
    gold = sample(("a",), ("b",))
    pred = sample(("b",), ("c",), ("c",))

    assert differing_rows(gold, pred) == ((True, False), (False, True, True))


def test_values_compare_like_ex() -> None:
    assert differing_rows(sample((1,)), sample((1.0,))) == ((False,), (False,))


def test_only_rows_checked_against_a_complete_sample_are_marked() -> None:
    gold = sample(("a",), ("b",))
    pred = sample(("c",), total=25)  # only part of the predicted rows is stored

    gold_marks, pred_marks = differing_rows(gold, pred)

    assert gold_marks == (False, False)  # "a" may be among the unseen rows
    assert pred_marks == (True,)  # gold is complete, and "c" is not in it


def test_nothing_is_marked_when_widths_differ_or_a_query_failed() -> None:
    gold = sample(("a",))
    wide = sample(("a", 1))

    assert differing_rows(gold, wide) == ((False,), (False,))
    failure = QueryFailure("timeout", "did not finish within 30 s")
    assert differing_rows(gold, failure) == ((False,), ())
