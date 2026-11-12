"""The reference documents must match the code they describe (ADR 0041).

Documentation is hand-written Markdown, so these tests catch drift: a public
name, a CLI option or a run file field that the documents do not mention.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

import text2sql_eval

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs/reference"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_api_reference_has_a_section_for_exactly_the_public_names() -> None:
    headings = re.findall(r"^### `([^`]+)`$", read(REFERENCE / "api.md"), re.MULTILINE)

    assert sorted(headings) == sorted(text2sql_eval.__all__)
    assert len(headings) == len(set(headings))


@pytest.mark.parametrize("command", ["eval", "report", "compare"])
def test_cli_reference_mentions_every_option(command: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "text2sql_eval.cli.main", command, "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    usage = result.stdout.split("examples:")[0]
    options = set(re.findall(r"--[a-z][a-z-]*", usage)) - {"--help"}
    doc = read(REFERENCE / "cli.md")

    assert options
    for option in options:
        # Written as `--option` or `--option VALUE` in a table or code span.
        assert re.search(rf"`{re.escape(option)}[ `]", doc), option


def format_keys(value: object, found: set[str]) -> set[str]:
    """Every object key in a run file, except inside user data (meta)."""
    if isinstance(value, dict):
        # Parsed JSON: object keys are strings and values any JSON value, so
        # this narrowing is exact (the same reasoning as datasets/_json.py).
        for key, child in cast("dict[str, object]", value).items():
            found.add(key)
            if key not in ("meta", "pred_meta"):
                format_keys(child, found)
    elif isinstance(value, list):
        for child in cast("list[object]", value):
            format_keys(child, found)
    return found


@pytest.mark.parametrize("mode", ["evidence", "no-evidence"])
def test_run_file_reference_mentions_every_field(mode: str) -> None:
    path = ROOT / f"examples/results/gpt-4o-mini-{mode}.run.json"
    keys = format_keys(json.loads(read(path)), set())
    doc = read(REFERENCE / "run-file.md")

    assert "cases" in keys and "relation" in keys
    for key in keys:
        # In the prose or tables as `key`; the JSON examples alone do not count.
        assert f"`{key}`" in doc, key


# --- links ---------------------------------------------------------------------


def markdown_files() -> list[Path]:
    """Markdown files of the repository, outside hidden and build folders."""
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not any(
            part.startswith(".") or part in ("dist", "build")
            for part in path.relative_to(ROOT).parts
        )
    )


def without_code(text: str) -> str:
    """The text outside fenced code blocks, where links and headings live."""
    return re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)


def anchor(heading: str) -> str:
    """GitHub's anchor for a heading: lower-case, punctuation dropped, - for spaces."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    headings = re.findall(r"^#+ (.+)$", without_code(read(path)), re.MULTILINE)
    return {anchor(heading) for heading in headings}


@pytest.mark.parametrize(
    "path", markdown_files(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_relative_links_point_at_existing_files_and_headings(path: Path) -> None:
    links = re.findall(r"\]\(([^)\s]+)\)", without_code(read(path)))
    for link in links:
        if re.match(r"[a-z]+:", link):  # http:, https:, mailto:
            continue
        target, _, fragment = link.partition("#")
        file = (path.parent / target).resolve() if target else path
        assert file.exists(), f"{link}: no such file"
        if fragment and file.suffix == ".md":
            assert fragment in anchors(file), f"{link}: no such heading"
