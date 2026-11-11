"""Keep spreadsheet programs from running CSV cells as formulas (ADR 0040).

Excel reads a cell that starts with ``=``, ``+``, ``-`` or ``@`` (and a few
others) as a formula, so a predicted SQL such as ``=HYPERLINK(...)`` or one
starting with a ``--`` comment would run or show ``#NAME?``. Following OWASP's
advice on CSV injection, such cells get a leading apostrophe, which Excel
hides and which makes it show the cell as text.
"""

from __future__ import annotations

FORMULA_STARTS = frozenset("=+-@\t\r\n＝＋－＠")
"""First characters that make a spreadsheet treat a cell as a formula.

The list, full-width forms included, is OWASP's (checked 2026-11-11).
"""


def excel_safe(cell: str) -> str:
    """``cell`` with a leading ``'`` if its first character starts a formula.

    Only the first character matters; ``=`` inside a cell is left alone.

    Example:
        >>> excel_safe("=HYPERLINK(\\"http://example.com\\")")
        '\\'=HYPERLINK("http://example.com")'
        >>> excel_safe("SELECT name FROM hero WHERE id = 1")
        'SELECT name FROM hero WHERE id = 1'
    """
    if cell and cell[0] in FORMULA_STARTS:
        return "'" + cell
    return cell
