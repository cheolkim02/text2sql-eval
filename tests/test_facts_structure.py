from text2sql_eval.facts.structure import (
    STRUCTURE_LABELS_KO,
    Fact,
    parse,
    shape_of,
    structural_facts,
)


def kinds(gold: str, pred: str) -> list[str]:
    return [fact.kind for fact in structural_facts(gold, pred).facts]


# --- where_value -------------------------------------------------------------


def test_where_value_reports_a_literal_that_differs_only_in_case() -> None:
    report = structural_facts(
        "SELECT id FROM superpower WHERE power_name = 'Cryokinesis'",
        "SELECT id FROM superpower WHERE power_name = 'cryokinesis';",
    )

    assert report.facts == (
        Fact(
            "where_value",
            gold="power_name = 'Cryokinesis'",
            pred="power_name = 'cryokinesis'",
        ),
    )


def test_where_value_sees_through_table_aliases() -> None:
    report = structural_facts(
        "SELECT T1.name FROM superhero AS T1 WHERE T1.gender = 'Male'",
        "SELECT s.name FROM superhero s WHERE s.gender = 'Female'",
    )

    assert report.facts == (
        Fact(
            "where_value",
            gold="superhero.gender = 'Male'",
            pred="superhero.gender = 'Female'",
        ),
    )


def test_where_value_matches_column_and_operator_in_either_order() -> None:
    assert kinds("SELECT 1 FROM t WHERE x > 180", "SELECT 1 FROM t WHERE 200 < x") == []
    assert kinds("SELECT 1 FROM t WHERE x > 180", "SELECT 1 FROM t WHERE x > 200") == [
        "where_value"
    ]


def test_where_value_handles_in_lists_and_wrapped_columns() -> None:
    assert kinds(
        "SELECT 1 FROM t WHERE e IN ('cl', 'br')", "SELECT 1 FROM t WHERE e IN ('cl')"
    ) == ["where_value"]
    assert kinds(
        "SELECT 1 FROM t WHERE LOWER(g) = 'male'",
        "SELECT 1 FROM t WHERE LOWER(g) = 'm'",
    ) == ["where_value"]


def test_where_value_compares_every_condition_on_the_same_column() -> None:
    # Two conditions on one column and operator: all of them count, not the last.
    same = "SELECT 1 FROM t WHERE year = 2010 OR year = 2011"
    assert kinds(same, same.replace("1 FROM", "2 FROM")) == []
    # Case #321: the prediction does use atom_id = 'TR000_2'.
    assert "where_value" not in kinds(
        "SELECT 1 FROM c WHERE c.atom_id = 'TR000_2' AND c.atom_id2 = 'TR000_4'",
        "SELECT 1 FROM a AS a1, a AS a2 "
        "WHERE a1.atom_id = 'TR000_2' AND a2.atom_id = 'TR000_4'",
    )


def test_where_value_counts_a_condition_inside_a_subquery_once() -> None:
    # The outer WHERE contains the subquery's WHERE; its condition is one fact.
    report = structural_facts(
        "SELECT name FROM hero WHERE eye_id = (SELECT id FROM colour WHERE c = 'Blue')",
        "SELECT name FROM hero WHERE eye_id = (SELECT id FROM colour WHERE c = 'blue')",
    )

    assert report.facts == (Fact("where_value", gold="c = 'Blue'", pred="c = 'blue'"),)


def test_where_value_lists_every_predicted_value_the_gold_does_not_use() -> None:
    report = structural_facts(
        "SELECT 1 FROM t WHERE year = 2010",
        "SELECT 1 FROM t WHERE year = 2011 OR year = 2012",
    )

    assert report.facts == (
        Fact("where_value", gold="year = 2010", pred="year = 2011, year = 2012"),
    )


def test_where_value_ignores_conditions_without_a_literal_or_with_other_columns() -> (
    None
):
    # A join condition in WHERE and an IN (subquery) carry no comparable value;
    # the subquery's different column is a `columns` difference, not a value one.
    assert kinds(
        "SELECT 1 FROM a, b WHERE a.id = b.id AND a.x IN (SELECT y FROM c)",
        "SELECT 1 FROM a, b WHERE a.id = b.id AND a.x IN (SELECT z FROM c)",
    ) == ["columns"]


# --- tables_joins ------------------------------------------------------------


def test_tables_joins_reports_extra_table_and_join() -> None:
    report = structural_facts(
        "SELECT COUNT(bond_id) FROM bond t",
        "SELECT COUNT(bond.bond_id) FROM bond JOIN connected ON bond.bond_id = connected.bond_id",
    )

    assert report.facts == (
        Fact(
            "tables_joins",
            gold="tables: bond; joins: 0",
            pred="tables: bond, connected; joins: 1",
        ),
    )


def test_tables_joins_ignores_alias_and_case_and_cte_names() -> None:
    assert kinds("SELECT 1 FROM Superhero AS T1", "SELECT 1 FROM superhero s") == []
    assert (
        kinds(
            "WITH x AS (SELECT 1 FROM t) SELECT * FROM x",
            "SELECT 1 FROM t",
        )
        == []
    )


# --- aggregation -------------------------------------------------------------


def test_aggregation_reports_different_aggregate_sets() -> None:
    report = structural_facts(
        "SELECT CAST(SUM(height_cm) AS REAL) / COUNT(id) FROM superhero",
        "SELECT AVG(height_cm) AS average_height FROM superhero",
    )

    assert report.facts == (
        Fact("columns", gold="id", pred="(none)"),
        Fact("aggregation", gold="COUNT(id), SUM(height_cm)", pred="AVG(height_cm)"),
    )


def test_aggregation_ignores_repetition_case_and_table_qualifiers() -> None:
    assert (
        kinds(
            "SELECT COUNT(*), COUNT(*), SUM(T1.x) FROM t AS T1",
            "SELECT count(*), sum(x) FROM T",
        )
        == []
    )


# --- order_limit -------------------------------------------------------------


def test_order_limit_reports_a_missing_clause() -> None:
    report = structural_facts(
        "SELECT superhero_name FROM superhero ORDER BY height_cm DESC LIMIT 1",
        "SELECT superhero_name FROM superhero",
    )

    assert Fact(
        "order_limit", gold="ORDER BY height_cm DESC LIMIT 1", pred="(none)"
    ) in (report.facts)


def test_order_limit_reports_a_different_limit() -> None:
    assert kinds(
        "SELECT a FROM t ORDER BY a LIMIT 1", "SELECT a FROM t ORDER BY a LIMIT 5"
    ) == ["order_limit"]


# --- whole reports ----------------------------------------------------------


def test_identical_queries_up_to_normalization_have_no_facts() -> None:
    report = structural_facts(
        "SELECT T.atom_id FROM atom AS T WHERE T.molecule_id = 'TR186'",
        "select atom_id from ATOM where molecule_id = 'TR186' ;",
    )

    assert report.facts == ()
    assert report.parse_failed is None


def test_columns_lists_what_each_side_uses_alone() -> None:
    report = structural_facts(
        "SELECT T.atom_id FROM atom AS T WHERE T.molecule_id = 'TR186'",
        "SELECT atom_id, element FROM atom WHERE molecule_id = 'TR186'",
    )

    assert report.facts == (Fact("columns", gold="(none)", pred="element"),)


def test_columns_reports_a_wrong_column_in_any_clause() -> None:
    report = structural_facts(
        "SELECT name FROM superhero WHERE height_cm > 200",
        "SELECT name FROM superhero WHERE weight_kg > 200",
    )

    assert report.facts == (Fact("columns", gold="height_cm", pred="weight_kg"),)


def test_columns_ignore_aliases_qualifiers_and_case() -> None:
    assert (
        kinds(
            "SELECT T1.Name AS n FROM superhero AS T1 ORDER BY n",
            "SELECT name AS n FROM Superhero ORDER BY n",
        )
        == []
    )


def test_parse_failure_is_reported_not_raised() -> None:
    broken = "SELECT m.x FROM m WHERE e.name = 'women\\'s soccer'"

    assert structural_facts("SELECT 1", broken).parse_failed == "pred"
    assert structural_facts(broken, "SELECT 1").parse_failed == "gold"
    assert parse(broken) is None


def test_shape_of_a_subquery_includes_its_tables_and_aggregates() -> None:
    query = parse("SELECT a FROM t WHERE x = (SELECT MAX(y) FROM u)")
    assert query is not None

    shape = shape_of(query)

    assert shape.tables == {"t", "u"}
    assert shape.aggregates == {"MAX(y)"}
    assert shape.conditions == ()  # the value side is a subquery, not a literal


def test_every_fact_kind_has_a_korean_label() -> None:
    assert set(STRUCTURE_LABELS_KO) == {
        "where_value",
        "tables_joins",
        "columns",
        "aggregation",
        "order_limit",
    }
