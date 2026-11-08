"""Errors raised when user-supplied input cannot be used."""

from __future__ import annotations

from pathlib import Path


class InputError(Exception):
    """An input file is malformed or does not match the dataset.

    The message says where the problem is (file, and line or item when known),
    what is wrong, and how to fix it, so it can be shown to users as is.

    Example:
        >>> err = InputError(Path("preds.jsonl"), "missing field 'sql'",
        ...                  location="line 3", hint="add an 'sql' string")
        >>> print(err)
        preds.jsonl, line 3: missing field 'sql'
          hint: add an 'sql' string
    """

    def __init__(
        self,
        path: Path,
        problem: str,
        *,
        location: str | None = None,
        hint: str | None = None,
    ) -> None:
        self.path = path
        self.problem = problem
        self.location = location
        self.hint = hint
        super().__init__(self._format())

    def _format(self) -> str:
        where = (
            str(self.path) if self.location is None else f"{self.path}, {self.location}"
        )
        message = f"{where}: {self.problem}"
        if self.hint is not None:
            message += f"\n  hint: {self.hint}"
        return message
