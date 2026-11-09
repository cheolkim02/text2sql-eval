#!/usr/bin/env sh
# Run every check that CI runs, in the same order. Usage: sh scripts/check.sh
set -eu
uv run ruff check .
uv run ruff format --check .
uv run --group examples pyright
uv run pytest
