#!/usr/bin/env sh
# Install the built wheel into a fresh Python 3.11 environment, without the
# dev dependencies, and run the CLI end to end on part of the example data
# (ADR 0044). CI runs it on every PR and the release workflow before
# publishing (ADR 0046). Usage, after `uv build`: sh scripts/smoke_wheel.sh
set -eu

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

uv venv --quiet --python 3.11 "$work/venv"
uv pip install --quiet --python "$work/venv" dist/*.whl
cli="$work/venv/bin/text2sql-eval"
"$cli" --version

# Prediction 211 never finishes (examples/results/README.md); leave it out.
head -n 40 examples/results/gpt-4o-mini-evidence.jsonl \
  | grep -v '"id": "211"' > "$work/pred.jsonl"
"$cli" eval --dataset examples/bird-mini/dev.json \
  --db-dir examples/bird-mini/dev_databases \
  --pred "$work/pred.jsonl" --allow-missing --timeout 10 \
  --out "$work/run.json"
"$cli" report "$work/run.json" --html "$work/report.html" --csv "$work/report.csv"
test "$(grep -c '<details class="case"' "$work/report.html")" -eq 432
echo "smoke test passed: the wheel installs and runs eval and report"
