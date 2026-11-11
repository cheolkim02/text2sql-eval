"""What to highlight in the report: differing SQL clauses and result rows (ADR 0039).

Highlighting is display only. It never changes a verdict, an output
difference, a SQL structure difference or a flag.

Clauses are compared after the same normalization as the SQL structure
differences (table aliases resolved, identifiers lower-cased, column
qualifiers dropped), so ``T1.name`` and ``s.name`` are not a difference.
Writing order that SQLite ignores is not a difference either: the order of
conditions joined by AND, the two sides of ``=``, the order of inner joins,
and ``INNER JOIN`` versus ``JOIN``. Only the outer query's clauses are
compared; a subquery belongs to the clause it sits in.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from sqlglot import exp

# sqlglot 30's node base class; see the note in facts/structure.py.
from sqlglot.expressions.core import Expr

from text2sql_eval.facts.structure import DIALECT, normalize, unqualified
from text2sql_eval.runfile import QuerySummary, ResultSample

Clause = Literal["with", "select", "from", "where", "group", "having", "order", "limit"]

# First words of the lines that start each clause in sqlglot's pretty output.
# FROM and every kind of JOIN form one clause, as do LIMIT and OFFSET.
_CLAUSE_STARTS: tuple[tuple[str, Clause], ...] = (
    ("WITH", "with"),
    ("SELECT", "select"),
    ("FROM", "from"),
    ("WHERE", "where"),
    ("GROUP BY", "group"),
    ("HAVING", "having"),
    ("ORDER BY", "order"),
    ("LIMIT", "limit"),
    ("OFFSET", "limit"),
)
# Clauses held in one node under the same name in sqlglot's Select.args;
# WHERE and HAVING are compared as conditions instead.
_SINGLE_NODE_CLAUSES: tuple[Clause, ...] = ("group", "order")
_JOIN_WORDS = frozenset({"JOIN", "INNER", "LEFT", "RIGHT", "FULL", "CROSS", "NATURAL"})


def differing_clauses(gold: Expr, pred: Expr) -> frozenset[Clause]:
    """Clauses whose normalized SQL differs, or that only one query has.

    Empty when either query is not a plain SELECT (for example a UNION),
    because its clauses cannot be lined up with the other query's.

    Example:
        >>> differing_clauses(
        ...     parse("SELECT T1.name FROM hero AS T1 WHERE T1.power = 'Fly'"),
        ...     parse("SELECT h.name FROM hero AS h WHERE h.power = 'fly'"),
        ... )
        frozenset({'where'})
    """
    if not isinstance(gold, exp.Select) or not isinstance(pred, exp.Select):
        return frozenset()
    gold_parts = _clause_texts(gold)
    pred_parts = _clause_texts(pred)
    return frozenset(
        clause
        for clause in gold_parts.keys() | pred_parts.keys()
        if gold_parts.get(clause) != pred_parts.get(clause)
    )


def clause_blocks(pretty_sql: str) -> list[tuple[Clause | None, str]]:
    """Split sqlglot's pretty output into one block per outer clause.

    sqlglot starts each outer clause at the beginning of a line and indents
    everything inside it. Lines before the first known clause get ``None``.

    Example:
        >>> clause_blocks("SELECT\n  name\nFROM hero\nJOIN power\n  ON hero.id = power.id")
        [('select', 'SELECT\n  name'), ('from', 'FROM hero\nJOIN power\n  ON hero.id = power.id')]
    """
    blocks: list[tuple[Clause | None, list[str]]] = []
    for line in pretty_sql.split("\n"):
        clause = _clause_starting(line)
        if clause is not None and (not blocks or blocks[-1][0] != clause):
            blocks.append((clause, [line]))
        elif blocks:
            blocks[-1][1].append(line)
        else:
            blocks.append((None, [line]))
    return [(clause, "\n".join(lines)) for clause, lines in blocks]


def differing_rows(
    gold: QuerySummary, pred: QuerySummary
) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    """For each stored row of each side, whether the other result lacks it.

    The run file keeps only the first rows of each result. A row missing from
    the other side's sample may still be in its full result, so a side's rows
    are marked only when the other side's sample is the complete result. Rows
    are compared like EX does (as tuples, ``1 == 1.0``), and only when both
    results have the same number of columns.

    Example:
        >>> gold = ResultSample(("name",), (("Surtur",), ("Ymir",)), row_count=2)
        >>> pred = ResultSample(("name",), (("Surtur",), ("Thor",)), row_count=2)
        >>> differing_rows(gold, pred)
        ((False, True), (False, True))
    """
    gold_marks = tuple(False for _ in _rows(gold))
    pred_marks = tuple(False for _ in _rows(pred))
    if not isinstance(gold, ResultSample) or not isinstance(pred, ResultSample):
        return gold_marks, pred_marks
    if len(gold.columns) != len(pred.columns) or not gold.columns:
        return gold_marks, pred_marks
    if _complete(pred):
        pred_rows = set(pred.rows)
        gold_marks = tuple(row not in pred_rows for row in gold.rows)
    if _complete(gold):
        gold_rows = set(gold.rows)
        pred_marks = tuple(row not in gold_rows for row in pred.rows)
    return gold_marks, pred_marks


def _clause_texts(select: exp.Select) -> dict[Clause, str]:
    """Normalized SQL of each clause the query has."""
    query = normalize(select)
    parts: dict[Clause, str] = {}
    with_ = query.args.get("with_")
    if isinstance(with_, Expr):
        parts["with"] = unqualified(with_)
    # Output column names (AS ...) do not matter to EX, so aliases are dropped.
    columns = ", ".join(unqualified(e.unalias()) for e in query.expressions)
    distinct = "DISTINCT " if query.args.get("distinct") else ""
    parts["select"] = distinct + columns
    sources = _sources_text(query)
    if sources is not None:
        parts["from"] = sources
    for clause in ("where", "having"):
        node = query.args.get(clause)
        if isinstance(node, Expr):
            parts[clause] = _condition_text(node.this, unqualified)
    for clause in _SINGLE_NODE_CLAUSES:
        node = query.args.get(clause)
        if isinstance(node, Expr):
            parts[clause] = unqualified(node)
    limits = [query.args.get("limit"), query.args.get("offset")]
    if any(isinstance(node, Expr) for node in limits):
        parts["limit"] = " ".join(
            unqualified(node) for node in limits if isinstance(node, Expr)
        )
    return parts


def _sources_text(query: Expr) -> str | None:
    """FROM and JOINs, where the order of inner joins does not matter.

    Join conditions keep their table qualifiers: in ``ON`` they say which
    tables are joined. LEFT, RIGHT and FULL joins keep their written order.
    """
    from_ = query.args.get("from_")
    joins = [j for j in query.args.get("joins") or () if isinstance(j, exp.Join)]
    if not isinstance(from_, exp.From) and not joins:
        return None
    tables = [_qualified(from_.this)] if isinstance(from_, exp.From) else []
    conditions: list[str] = []
    outer: list[str] = []
    for join in joins:
        on = join.args.get("on")
        using = [u for u in join.args.get("using") or () if isinstance(u, Expr)]
        join_conditions = (
            _conjunct_texts(on, _qualified) if isinstance(on, Expr) else []
        )
        join_conditions.extend(f"USING {_qualified(u)}" for u in using)
        side = str(join.args.get("side") or "").upper()
        if side:
            outer.append(
                f"{side} JOIN {_qualified(join.this)} ON "
                + " AND ".join(sorted(join_conditions))
            )
        else:  # inner, CROSS or plain JOIN: all the same to SQLite
            tables.append(_qualified(join.this))
            conditions.extend(join_conditions)
    inner = ", ".join(sorted(tables)) + " ON " + " AND ".join(sorted(conditions))
    return "; ".join([inner, *outer])


def _condition_text(node: Expr, text: Callable[[Expr], str]) -> str:
    return " AND ".join(sorted(_conjunct_texts(node, text)))


def _conjunct_texts(node: Expr, text: Callable[[Expr], str]) -> list[str]:
    """Each condition joined by AND, as text, with ``=`` sides in a fixed order."""
    return [text(_symmetric(part, text)) for part in _conjuncts(node)]


def _conjuncts(node: Expr) -> list[Expr]:
    node = node.unnest()
    if isinstance(node, exp.And):
        return [*_conjuncts(node.left), *_conjuncts(node.right)]
    return [node]


def _symmetric(node: Expr, text: Callable[[Expr], str]) -> Expr:
    """A copy in which the two sides of every ``=`` are ordered by their text."""

    def order(child: Expr) -> Expr:
        if isinstance(child, exp.EQ) and text(child.left) > text(child.right):
            return exp.EQ(this=child.right.copy(), expression=child.left.copy())
        return child

    return node.copy().transform(order)


def _qualified(node: Expr) -> str:
    return node.sql(dialect=DIALECT)


def _clause_starting(line: str) -> Clause | None:
    """The clause a line starts, if it is an outer clause line."""
    if not line or line[0].isspace():
        return None
    for word, clause in _CLAUSE_STARTS:
        if line == word or line.startswith(word + " "):
            return clause
    if line.split(" ", 1)[0] in _JOIN_WORDS and " JOIN" in f" {line}":
        return "from"
    return None


def _rows(result: QuerySummary) -> tuple[tuple[object, ...], ...]:
    return result.rows if isinstance(result, ResultSample) else ()


def _complete(result: ResultSample) -> bool:
    return result.row_count <= len(result.rows)
