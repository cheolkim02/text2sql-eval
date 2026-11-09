"""Single-prompt baseline: ask an OpenAI model for one SQLite query per question.

This is an example that *produces* prediction files for text2sql-eval; the
tool itself never calls a model (ADR 0004). It writes the JSONL prediction
format (ADR 0018), with the response's model snapshot, token counts and
latency in each line's ``meta``.

The two committed baselines differ only in whether BIRD's evidence is in the
prompt (ADR 0028, model choice in ADR 0030):

    OPENAI_API_KEY=... uv run --group examples python examples/baseline/predict.py \\
        --dataset examples/bird-mini/dev.json \\
        --db-dir examples/bird-mini/dev_databases \\
        --evidence --out examples/results/gpt-4o-mini-evidence.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam

from text2sql_eval.datasets.bird import Case, load_bird

MODEL = "gpt-4o-mini"
# USD per 1M tokens, from OpenAI's pricing page on 2026-11-09; for the printed
# estimate only. The usage numbers saved in each line are the real record.
PRICE_INPUT_PER_M = 0.15
PRICE_OUTPUT_PER_M = 0.60

SYSTEM_PROMPT = (
    "You are a SQLite expert. Answer with one SQLite query and nothing else."
)

_FENCE = re.compile(r"```(?:sql|sqlite)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def schema_ddl(db_path: Path) -> str:
    """The database's CREATE TABLE statements, in name order."""
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        rows: list[tuple[str]] = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'table' AND sql IS NOT NULL ORDER BY name"
        ).fetchall()
    return "\n".join(f"{sql};" for (sql,) in rows)


def build_messages(
    case: Case, schema: str, *, with_evidence: bool
) -> list[ChatCompletionMessageParam]:
    """The prompt. The two baselines differ only in the Hint line."""
    parts = [f"Database schema:\n{schema}"]
    if with_evidence and case.evidence:
        parts.append(f"Hint: {case.evidence}")
    parts.append(f"Question: {case.question}")
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


def extract_sql(text: str) -> str:
    """Take the SQL out of a reply and put it on one line.

    Code fences are removed. Line breaks become single spaces so the query fits
    one prediction line; spacing inside a line is kept, so string literals are
    unchanged unless they span lines.
    """
    match = _FENCE.search(text)
    sql = match.group(1) if match else text
    return re.sub(r"\s*\n\s*", " ", sql.strip())


@dataclass(frozen=True)
class Line:
    """One prediction line plus the usage numbers needed for the cost report."""

    case_id: str
    sql: str
    meta: dict[str, object]
    input_tokens: int
    output_tokens: int
    failed: bool

    def to_json(self) -> str:
        record = {"id": self.case_id, "sql": self.sql, "meta": self.meta}
        return json.dumps(record, ensure_ascii=False)


def predict(client: OpenAI, case: Case, schema: str, *, with_evidence: bool) -> Line:
    """One prediction. An API failure becomes an empty prediction with the error."""
    started = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=build_messages(case, schema, with_evidence=with_evidence),
            temperature=0,
            seed=0,
            max_tokens=512,
        )
    except OpenAIError as error:
        meta: dict[str, object] = {"error": f"{type(error).__name__}: {error}"}
        return Line(case.id, "", meta, 0, 0, failed=True)
    choice = response.choices[0]
    input_tokens = response.usage.prompt_tokens if response.usage else 0
    output_tokens = response.usage.completion_tokens if response.usage else 0
    meta = {
        "model": response.model,
        "system_fingerprint": response.system_fingerprint,
        "finish_reason": choice.finish_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": round((time.monotonic() - started) * 1000),
    }
    sql = extract_sql(choice.message.content or "")
    return Line(case.id, sql, meta, input_tokens, output_tokens, failed=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Single-prompt OpenAI baseline.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--db-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--evidence",
        action=argparse.BooleanOptionalAction,
        required=True,
        help="include BIRD's evidence as a hint (--no-evidence to leave it out)",
    )
    parser.add_argument(
        "--limit", type=int, help="only the first N questions (trial run)"
    )
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)

    cases = load_bird(args.dataset).cases[: args.limit]
    schemas = {
        db_id: schema_ddl(args.db_dir / db_id / f"{db_id}.sqlite")
        for db_id in sorted({case.db_id for case in cases})
    }
    client = OpenAI()  # reads OPENAI_API_KEY; retries rate limits and 5xx itself

    def run(case: Case) -> Line:
        return predict(client, case, schemas[case.db_id], with_evidence=args.evidence)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        lines = list(pool.map(run, cases))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(line.to_json() + "\n" for line in lines), encoding="utf-8"
    )
    _report(lines, args.out)
    return 0


def _report(lines: list[Line], out: Path) -> None:
    input_tokens = sum(line.input_tokens for line in lines)
    output_tokens = sum(line.output_tokens for line in lines)
    failures = sum(line.failed for line in lines)
    cost = (input_tokens * PRICE_INPUT_PER_M + output_tokens * PRICE_OUTPUT_PER_M) / 1e6
    print(
        f"{len(lines)} predictions -> {out}\n"
        f"tokens: {input_tokens} in, {output_tokens} out; "
        f"estimated cost ${cost:.4f} (prices of 2026-11-09)\n"
        f"API failures (written as empty predictions): {failures}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    sys.exit(main())
