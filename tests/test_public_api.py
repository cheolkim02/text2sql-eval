"""The public API is exactly ``__all__`` (ADR 0043), documented and fully typed."""

import inspect
from typing import Any, get_args, get_type_hints

import pytest

import text2sql_eval

AGREED = {
    "evaluate_files",
    "read_run",
    "write_run",
    "compare_runs",
    "write_html_report",
    "write_report_csv",
    "write_comparison_csv",
    "status_of",
    "Run",
    "CaseRecord",
    "Summary",
    "FileRef",
    "RunSettings",
    "ResultSample",
    "QueryFailure",
    "SqlValue",
    "PredictionState",
    "Verdict",
    "Correct",
    "Incorrect",
    "ExecError",
    "Flag",
    "FlagKind",
    "CaseDiff",
    "OutputDiff",
    "OutputDifference",
    "Relation",
    "StructureReport",
    "Fact",
    "FactKind",
    "Comparison",
    "CaseChange",
    "Change",
    "GroupEx",
    "InputError",
    "__version__",
}

PUBLIC = [name for name in text2sql_eval.__all__ if name != "__version__"]


def test_all_lists_exactly_the_agreed_names_once() -> None:
    # Changing the public API means changing this set on purpose.
    assert set(text2sql_eval.__all__) == AGREED
    assert len(text2sql_eval.__all__) == len(AGREED)


@pytest.mark.parametrize("name", PUBLIC)
def test_public_name_is_importable_from_the_package(name: str) -> None:
    assert hasattr(text2sql_eval, name)


@pytest.mark.parametrize("name", PUBLIC)
def test_public_functions_have_examples_and_classes_have_docstrings(
    name: str,
) -> None:
    obj = getattr(text2sql_eval, name)
    if inspect.isfunction(obj):
        assert "Example" in (inspect.getdoc(obj) or "")
    elif inspect.isclass(obj):
        own = obj.__dict__.get("__doc__") or ""
        # A dataclass without a docstring gets its signature as __doc__.
        assert own and not own.startswith(f"{name}(")


def contains_any(annotation: object) -> bool:
    return annotation is Any or any(contains_any(a) for a in get_args(annotation))


def test_the_any_check_finds_nested_any() -> None:
    assert contains_any(dict[str, Any])
    assert contains_any(tuple[int, list[Any]] | None)
    assert not contains_any(dict[str, object])


def annotated(obj: object) -> list[object]:
    """Everything with annotations that the public object exposes."""
    if not inspect.isclass(obj):
        return [obj]
    members: list[object] = [obj]
    for member in vars(obj).values():
        if isinstance(member, property):
            members.append(member.fget)
        elif inspect.isfunction(member):
            members.append(member)
    return members


@pytest.mark.parametrize("name", PUBLIC)
def test_public_signatures_and_fields_never_use_any(name: str) -> None:
    obj = getattr(text2sql_eval, name)
    if not (inspect.isfunction(obj) or inspect.isclass(obj)):
        # A type alias such as Verdict or FlagKind.
        assert not contains_any(obj)
        return
    for member in annotated(obj):
        hints = get_type_hints(member)
        assert not any(contains_any(hint) for hint in hints.values()), (
            member,
            hints,
        )
