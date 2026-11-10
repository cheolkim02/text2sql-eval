from text2sql_eval.execution.executor import QueryFailure, Rows, SqlValue
from text2sql_eval.facts.result import CATEGORY_LABELS_KO, ResultDiff, classify


def rows(*values: tuple[SqlValue, ...], columns: tuple[str, ...] = ("c",)) -> Rows:
    return Rows(columns=columns, rows=values)


def test_failed_prediction_is_execution_failed() -> None:
    diff = classify(rows((1,)), QueryFailure("error", "no such column: x"))

    assert diff.category == "execution_failed"
    assert (diff.gold_rows, diff.pred_rows) == (1, 0)


def test_empty_prediction_against_non_empty_gold() -> None:
    diff = classify(rows((19,)), Rows(("id",), ()))

    assert diff.category == "empty_result"


def test_column_mismatch_when_gold_rows_are_contained() -> None:
    gold = rows(("TR186_1",), ("TR186_10",), columns=("atom_id",))
    pred = rows(("c", "TR186_1"), ("c", "TR186_10"), columns=("element", "atom_id"))

    diff = classify(gold, pred)

    assert diff == ResultDiff(
        "column_mismatch",
        gold_columns=1,
        pred_columns=2,
        gold_rows=2,
        pred_rows=2,
        gold_contained=True,
    )


def test_column_mismatch_when_gold_rows_are_not_contained() -> None:
    gold = rows(("Grant", "Gilmour"), columns=("first_name", "last_name"))
    pred = rows(("Grant Gilmour",), columns=("full_name",))

    diff = classify(gold, pred)

    assert diff.category == "column_mismatch"
    assert diff.gold_contained is False


def test_column_containment_is_skipped_for_very_wide_predictions() -> None:
    gold = rows((1,))
    pred = Rows(tuple(f"c{i}" for i in range(9)), ((1, 2, 3, 4, 5, 6, 7, 8, 9),))

    assert classify(gold, pred).gold_contained is None


def test_single_value_differs() -> None:
    diff = classify(rows((247.05,)), rows((267.75,)))

    assert diff.category == "single_value_differs"
    assert diff.relation is None


def test_single_value_rule_needs_one_column() -> None:
    # Two columns, one row: a row-set difference, not "single value".
    gold = rows((1, 2), columns=("a", "b"))
    pred = rows((1, 3), columns=("a", "b"))

    assert classify(gold, pred).category == "row_set_differs"


def test_row_set_relations() -> None:
    gold = rows(("n",), ("h",), ("pb",))

    assert classify(gold, rows(("pb",))).relation == "subset"
    assert classify(gold, rows(("n",), ("h",), ("pb",), ("c",))).relation == "superset"
    assert classify(gold, rows(("n",), ("x",))).relation == "overlap"
    assert classify(gold, rows(("x",), ("y",))).relation == "disjoint"


def test_superset_counts_as_gold_contained() -> None:
    diff = classify(rows(("Surtur",)), rows(("Surtur",), ("Ymir",)))

    assert diff.category == "row_set_differs"
    assert diff.gold_contained is True
    assert diff.relation == "superset"


def test_every_category_has_a_korean_label() -> None:
    assert set(CATEGORY_LABELS_KO) == {
        "execution_failed",
        "empty_result",
        "column_mismatch",
        "single_value_differs",
        "row_set_differs",
    }
