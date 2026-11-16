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


# Absolute links to this repository's main branch, as README.md must use them.
# Group 1 is the path inside the repository.
SELF_LINK = re.compile(
    r"https://(?:github\.com/cheolkim02/text2sql-eval/(?:blob|tree)/main"
    r"|raw\.githubusercontent\.com/cheolkim02/text2sql-eval/main)/([^#]+)"
)


def links(text: str) -> list[str]:
    """Link and image targets outside code blocks: [text](target), ![alt](target)."""
    return re.findall(r"\]\(([^)\s]+)\)", without_code(text))


def broken_links(path: Path) -> list[str]:
    """Links in a Markdown file whose file or heading does not exist.

    Relative links resolve from the file. Absolute links to this repository
    are checked as files in the checkout; other URLs are not checked.
    """
    broken: list[str] = []
    for link in links(read(path)):
        if match := SELF_LINK.match(link):
            target = ROOT / match.group(1)
        elif re.match(r"[a-z]+:", link):  # other http:, https:, mailto:
            continue
        else:
            relative = link.partition("#")[0]
            target = (path.parent / relative).resolve() if relative else path
        fragment = link.partition("#")[2]
        if not target.exists():
            broken.append(f"{link}: no such file")
        elif fragment and target.suffix == ".md" and fragment not in anchors(target):
            broken.append(f"{link}: no such heading")
    return broken


@pytest.mark.parametrize(
    "path", markdown_files(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_links_point_at_existing_files_and_headings(path: Path) -> None:
    assert broken_links(path) == []


def test_broken_links_finds_missing_files_and_headings(tmp_path: Path) -> None:
    blob = "https://github.com/cheolkim02/text2sql-eval/blob/main"
    raw = "https://raw.githubusercontent.com/cheolkim02/text2sql-eval/main"
    page = tmp_path / "page.md"
    page.write_text(
        f"[ok]({blob}/README.md#3분-사용법) [ok](https://example.com/x)\n"
        f"[gone]({blob}/docs/missing.md) [gone]({blob}/README.md#no-such)\n"
        f"![gone]({raw}/docs/images/missing.png) [gone](missing.md)\n",
        encoding="utf-8",
    )

    assert broken_links(page) == [
        f"{blob}/docs/missing.md: no such file",
        f"{blob}/README.md#no-such: no such heading",
        f"{raw}/docs/images/missing.png: no such file",
        "missing.md: no such file",
    ]


def test_readme_links_are_absolute() -> None:
    # README.md is also the project page on PyPI, which cannot follow links
    # relative to the repository.
    relative = [
        link
        for link in links(read(ROOT / "README.md"))
        if not link.startswith("https://")
    ]
    assert relative == []
