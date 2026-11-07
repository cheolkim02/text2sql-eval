from importlib.metadata import version

import text2sql_eval


def test_version_matches_installed_metadata() -> None:
    assert text2sql_eval.__version__ == version("text2sql-eval")
