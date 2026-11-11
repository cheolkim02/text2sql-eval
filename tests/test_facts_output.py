from text2sql_eval.execution.executor import QueryFailure, Rows, SqlValue
from text2sql_eval.facts.output import OUTPUT_LABELS_KO, OutputDiff, compare_outputs


def rows(*values: tuple[SqlValue, ...], columns: tuple[str, ...] = ("c",)) -> Rows:
    return Rows(columns=columns, rows=values)


def test_failed_prediction_has_only_execution_failed() -> None:
    diff = compare_outputs(rows((1,)), QueryFailure("error", "no such column: x"))

    assert diff.differences == ("execution_failed",)
    assert (diff.gold_distinct_rows, diff.pred_distinct_rows) == (1, 0)


def test_empty_prediction() -> None:
    assert compare_outputs(rows((19,)), Rows(("id",), ())).differences == (
        "empty_result",
    )


def test_empty_prediction_with_a_different_width() -> None:
    diff = compare_outputs(rows((19,)), Rows(("id", "name"), ()))

    assert diff.differences == ("empty_result", "column_mismatch")


def test_no_prediction_is_only_an_empty_result() -> None:
    # Empty SQL runs and yields no columns at all; that is not a column problem.
    assert compare_outputs(rows((19,)), Rows((), ())).differences == ("empty_result",)


def test_extra_column_with_gold_rows_inside_is_only_a_column_mismatch() -> None:
    # #300: the prediction adds `element`; the gold atoms are all there.
    gold = rows(("TR186_1",), ("TR186_10",), columns=("atom_id",))
    pred = rows(("c", "TR186_1"), ("c", "TR186_10"), columns=("element", "atom_id"))

    assert compare_outputs(gold, pred) == OutputDiff(
        ("column_mismatch",),
        gold_columns=1,
        pred_columns=2,
        gold_distinct_rows=2,
        pred_distinct_rows=2,
        gold_contained=True,
    )


def test_different_width_and_different_content() -> None:
    # #1445: first and last name joined into one column.
    gold = rows(("Grant", "Gilmour"), columns=("first_name", "last_name"))
    pred = rows(("Grant Gilmour",), columns=("full_name",))

    diff = compare_outputs(gold, pred)

    assert diff.differences == ("column_mismatch", "row_set_differs")
    assert diff.gold_contained is False


def test_unknown_containment_claims_nothing_about_rows() -> None:
    gold = rows((1,))
    pred = Rows(tuple(f"c{i}" for i in range(9)), ((1, 2, 3, 4, 5, 6, 7, 8, 9),))

    diff = compare_outputs(gold, pred)

    assert diff.differences == ("column_mismatch",)
    assert diff.gold_contained is None


def test_single_value_differs() -> None:
    diff = compare_outputs(rows((247.05,)), rows((267.75,)))

    assert diff.differences == ("single_value_differs",)


def test_single_value_needs_one_column() -> None:
    gold = rows((1, 2), columns=("a", "b"))
    pred = rows((1, 3), columns=("a", "b"))

    assert compare_outputs(gold, pred).differences == ("row_set_differs",)


def test_tied_superset_has_two_differences() -> None:
    # #802: the tallest-hero tie returns both names.
    diff = compare_outputs(rows(("Surtur",)), rows(("Surtur",), ("Ymir",)))

    assert diff.differences == ("row_count_differs", "row_set_differs")
    assert diff.relation == "superset"
    assert diff.gold_contained is True


def test_same_count_different_rows() -> None:
    diff = compare_outputs(rows(("a",), ("b",)), rows(("a",), ("x",)))

    assert diff.differences == ("row_set_differs",)
    assert diff.relation == "overlap"


def test_row_counts_are_distinct_rows() -> None:
    # Duplicates do not change EX, so they do not count as a row-count difference.
    diff = compare_outputs(rows(("a",), ("b",)), rows(("a",), ("a",), ("x",)))

    assert "row_count_differs" not in diff.differences
    assert (diff.gold_distinct_rows, diff.pred_distinct_rows) == (2, 2)


def test_row_set_relations() -> None:
    gold = rows(("n",), ("h",), ("pb",))

    assert compare_outputs(gold, rows(("pb",))).relation == "subset"
    assert compare_outputs(gold, rows(("x",), ("y",))).relation == "disjoint"


def test_empty_gold_with_rows_predicted_makes_no_containment_claim() -> None:
    diff = compare_outputs(Rows(("c",), ()), rows(("x",)))

    assert diff.differences == ("row_count_differs", "row_set_differs")
    assert diff.gold_contained is None


def test_every_difference_has_a_korean_label() -> None:
    assert set(OUTPUT_LABELS_KO) == {
        "execution_failed",
        "empty_result",
        "column_mismatch",
        "row_count_differs",
        "single_value_differs",
        "row_set_differs",
    }
