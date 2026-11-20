"""SQL structure differences between gold and predicted SQL (ADR 0031, 0033).

Both queries are parsed with sqlglot (ADR 0032) and reduced to a small
``Shape``; the differences come from comparing shapes. Normalization is
deliberately minimal: identifier case, whitespace, a trailing semicolon and
table aliases. String literals keep their case, because a value that differs
only by case is exactly the kind of fact worth reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

# sqlglot 30's node base class, defined in expressions.core and star-imported
# without __all__, which pyright does not treat as a re-export.
from sqlglot.expressions.core import Expr

DIALECT = "sqlite"

FactKind = Literal[
    "where_value", "tables_joins", "columns", "aggregation", "order_limit"
]

STRUCTURE_LABELS_KO: dict[FactKind, str] = {
    "where_value": "WHERE 조건의 값이 다름",
    "tables_joins": "테이블·JOIN 구성이 다름",
    "columns": "사용한 컬럼이 다름",
    "aggregation": "집계 함수가 다름",
    "order_limit": "ORDER BY/LIMIT이 다름",
}


@dataclass(frozen=True)
class Fact:
    """One difference, with the evidence from each side as readable SQL fragments."""

    kind: FactKind
    gold: str
    pred: str


@dataclass(frozen=True)
class StructureReport:
    """Facts for one case, or the reason none could be produced."""

    facts: tuple[Fact, ...]
    parse_failed: Literal["gold", "pred"] | None = None


@dataclass(frozen=True)
class Condition:
    """A WHERE comparison between a column and literal value(s)."""

    column: str  # unqualified, lower-cased
    operator: str
    value: str  # the literal side as SQL, case preserved
    text: str  # the whole condition, normalized, for evidence


@dataclass(frozen=True)
class Shape:
    tables: frozenset[str]
    joins: int
    columns: frozenset[str]  # unqualified, lower-cased, select aliases removed
    conditions: tuple[Condition, ...]
    aggregates: frozenset[str]
    order: str | None
    limit: str | None


def structural_facts(gold_sql: str, pred_sql: str) -> StructureReport:
    """Compare two queries and report the v1 structural facts.

    Example:
        >>> report = structural_facts(
        ...     "SELECT id FROM superpower WHERE power_name = 'Cryokinesis'",
        ...     "SELECT id FROM superpower WHERE power_name = 'cryokinesis';",
        ... )
        >>> report.facts
        (Fact(kind='where_value', gold="power_name = 'Cryokinesis'", pred="power_name = 'cryokinesis'"),)
    """
    gold = parse(gold_sql)
    if gold is None:
        return StructureReport((), parse_failed="gold")
    pred = parse(pred_sql)
    if pred is None:
        return StructureReport((), parse_failed="pred")
    return StructureReport(tuple(compare(shape_of(gold), shape_of(pred))))


def parse(sql: str) -> Expr | None:
    """Parse one statement, or ``None`` when sqlglot cannot."""
    try:
        return sqlglot.parse_one(sql, read=DIALECT)
    except SqlglotError:
        return None


def shape_of(query: Expr) -> Shape:
    """Reduce a parsed query to the parts the facts compare."""
    query = normalize(query)
    cte_names = {cte.alias_or_name.lower() for cte in query.find_all(exp.CTE)}
    tables = frozenset(
        table.name.lower()
        for table in query.find_all(exp.Table)
        if table.name and table.name.lower() not in cte_names
    )
    joins = sum(1 for _ in query.find_all(exp.Join))
    # A select alias used later (ORDER BY percentage) parses as a column; it
    # names an output, not a table column, so it is not counted.
    aliases = {alias.alias.lower() for alias in query.find_all(exp.Alias)}
    columns = frozenset(
        column.name.lower()
        for column in query.find_all(exp.Column)
        if column.name and column.name.lower() not in aliases
    )
    # An outer WHERE also contains its subqueries' WHERE, so the same condition
    # is found twice; keep each once (dict.fromkeys keeps the order).
    conditions = tuple(
        dict.fromkeys(
            condition
            for where in query.find_all(exp.Where)
            for condition in _conditions(where)
        )
    )
    aggregates = frozenset(unqualified(agg) for agg in query.find_all(exp.AggFunc))
    order = query.args.get("order")
    limit = query.args.get("limit")
    return Shape(
        tables=tables,
        joins=joins,
        columns=columns,
        conditions=conditions,
        aggregates=aggregates,
        order=unqualified(order) if isinstance(order, Expr) else None,
        limit=unqualified(limit) if isinstance(limit, Expr) else None,
    )


def compare(gold: Shape, pred: Shape) -> list[Fact]:
    """The facts that distinguish two shapes, in a fixed order."""
    facts: list[Fact] = []
    facts.extend(_where_value_facts(gold, pred))
    if gold.tables != pred.tables or gold.joins != pred.joins:
        facts.append(
            Fact(
                "tables_joins",
                gold=_describe_tables(gold),
                pred=_describe_tables(pred),
            )
        )
    if gold.columns != pred.columns:
        # Only the columns one side uses and the other does not.
        facts.append(
            Fact(
                "columns",
                gold=", ".join(sorted(gold.columns - pred.columns)) or "(none)",
                pred=", ".join(sorted(pred.columns - gold.columns)) or "(none)",
            )
        )
    if gold.aggregates != pred.aggregates:
        facts.append(
            Fact(
                "aggregation",
                gold=", ".join(sorted(gold.aggregates)) or "(none)",
                pred=", ".join(sorted(pred.aggregates)) or "(none)",
            )
        )
    if (gold.order, gold.limit) != (pred.order, pred.limit):
        facts.append(
            Fact(
                "order_limit",
                gold=_describe_order(gold),
                pred=_describe_order(pred),
            )
        )
    return facts


def _where_value_facts(gold: Shape, pred: Shape) -> list[Fact]:
    """Same column and operator on both sides, different value.

    A column can have several conditions (``year = 2010 OR year = 2011``), so
    a gold value counts as matched if any predicted condition on that column
    and operator uses it, and the evidence lists the predicted values the gold
    does not use.
    """
    facts: list[Fact] = []
    for condition in gold.conditions:
        key = (condition.column, condition.operator)
        gold_values = {
            c.value for c in gold.conditions if (c.column, c.operator) == key
        }
        others = [c for c in pred.conditions if (c.column, c.operator) == key]
        if condition.value in {c.value for c in others}:
            continue
        unmatched = [c.text for c in others if c.value not in gold_values]
        if unmatched:
            facts.append(
                Fact("where_value", gold=condition.text, pred=", ".join(unmatched))
            )
    return facts


def _conditions(where: exp.Where) -> list[Condition]:
    found: list[Condition] = []
    for predicate in where.this.find_all(exp.Predicate):
        if isinstance(predicate, exp.In):
            column = predicate.this
            values = predicate.expressions
            if not isinstance(column, exp.Column) or not values:
                continue  # IN (subquery): no literal values to compare
            value = ", ".join(v.sql(dialect=DIALECT) for v in values)
        elif isinstance(predicate, exp.Binary):
            column, other = _column_and_value(predicate)
            if column is None or other is None:
                continue
            value = other.sql(dialect=DIALECT)
        else:
            continue
        found.append(
            Condition(
                column=column.name.lower(),
                operator=type(predicate).__name__.upper(),
                value=value,
                text=predicate.sql(dialect=DIALECT),
            )
        )
    return found


def _column_and_value(
    predicate: exp.Binary,
) -> tuple[exp.Column | None, Expr | None]:
    """Split ``col op literal`` (either order); ``None`` if it is not that shape."""
    left, right = predicate.left, predicate.right
    for column_side, value_side in ((left, right), (right, left)):
        column = _column_inside(column_side)
        if (
            column is not None
            and _has_literal(value_side)
            and not _has_column(value_side)
        ):
            return column, value_side
    return None, None


def _column_inside(node: Expr) -> exp.Column | None:
    """A column, possibly wrapped in a function such as ``LOWER(col)``."""
    if isinstance(node, exp.Column):
        return node
    columns = list(node.find_all(exp.Column))
    return columns[0] if len(columns) == 1 and not _has_subquery(node) else None


def _has_literal(node: Expr) -> bool:
    return node.find(exp.Literal) is not None


def _has_column(node: Expr) -> bool:
    return node.find(exp.Column) is not None


def _has_subquery(node: Expr) -> bool:
    return node.find(exp.Select) is not None


def normalize(query: Expr) -> Expr:
    """Resolve table aliases to table names and lower-case identifiers."""
    aliases = {
        table.alias.lower(): table.name.lower()
        for table in query.find_all(exp.Table)
        if table.alias
    }

    def rewrite(node: Expr) -> Expr:
        if isinstance(node, exp.Column) and node.table:
            real = aliases.get(node.table.lower())
            if real is not None:
                node.set("table", exp.to_identifier(real))
        if isinstance(node, exp.Table) and node.alias:
            node.set("alias", None)
        if isinstance(node, exp.Identifier):
            node.set("this", node.this.lower())
        return node

    return query.copy().transform(rewrite)


def unqualified(node: Expr) -> str:
    """SQL of ``node`` with table qualifiers dropped from columns.

    ``COUNT(bond_id)`` and ``COUNT(bond.bond_id)`` name the same thing in the
    aggregate and ORDER BY comparisons; a qualifier is not a difference.
    """

    def strip(child: Expr) -> Expr:
        if isinstance(child, exp.Column):
            child.set("table", None)
        return child

    return node.copy().transform(strip).sql(dialect=DIALECT)


def _describe_tables(shape: Shape) -> str:
    tables = ", ".join(sorted(shape.tables)) or "(none)"
    return f"tables: {tables}; joins: {shape.joins}"


def _describe_order(shape: Shape) -> str:
    parts = [part for part in (shape.order, shape.limit) if part]
    return " ".join(parts) if parts else "(none)"
