"""What differs between a wrong prediction and the gold answer (ADR 0031).

``result`` classifies from executed rows; ``structure`` compares parsed SQL.
Not part of the public API yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from text2sql_eval.facts.result import ResultDiff
from text2sql_eval.facts.structure import StructureReport


@dataclass(frozen=True)
class CaseDiff:
    """Everything the tool can say about why one case is not correct."""

    result: ResultDiff
    structure: StructureReport
