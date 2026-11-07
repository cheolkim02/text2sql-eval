"""Download the full BIRD dev set (all 11 databases, about 346 MB compressed).

The repository ships only a three-database subset in this folder. Use this
script when you want to evaluate on the whole dev set. The extracted layout
matches this folder, so the same paths work:

    uv run python examples/bird-mini/download_full_dev.py --out data/bird-dev

Data license: CC BY-SA 4.0 (see LICENSE and SOURCE.md in this folder).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

DEV_URL = "https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip"
# Checksum of the file downloaded on 2026-11-07 (release dev_20240627).
EXPECTED_SHA256 = "cdd6d19faeb45a23970b98d3ef6c40a87987c95459c2cf12076897a60cf5a630"
RELEASE_DIR = "dev_20240627/"
INNER_DB_ZIP = RELEASE_DIR + "dev_databases.zip"


def download(url: str, target: Path) -> str:
    """Stream ``url`` to ``target`` and return the file's SHA-256 hex digest."""
    digest = hashlib.sha256()
    with urllib.request.urlopen(url) as response, target.open("wb") as out:
        while chunk := response.read(1 << 20):
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest()


def extract(archive: Path, out_dir: Path) -> None:
    """Extract the release files and the nested database archive into ``out_dir``."""
    with zipfile.ZipFile(archive) as outer:
        for info in outer.infolist():
            if info.is_dir() or not info.filename.startswith(RELEASE_DIR):
                continue
            if info.filename == INNER_DB_ZIP:
                with zipfile.ZipFile(io.BytesIO(outer.read(info))) as inner:
                    _extract_members(inner, out_dir)
                continue
            target = _safe_target(out_dir, info.filename.removeprefix(RELEASE_DIR))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(outer.read(info))


def _safe_target(out_dir: Path, member: str) -> Path:
    """Resolve ``member`` under ``out_dir``, refusing paths that escape it."""
    target = (out_dir / member).resolve()
    # A crafted archive entry such as "../../x" must not write outside out_dir.
    if not target.is_relative_to(out_dir.resolve()):
        msg = f"unsafe path in archive: {member}"
        raise ValueError(msg)
    return target


def _extract_members(archive: zipfile.ZipFile, out_dir: Path) -> None:
    for info in archive.infolist():
        name = Path(info.filename)
        if info.is_dir() or name.name == ".DS_Store" or name.parts[0] == "__MACOSX":
            continue
        target = _safe_target(out_dir, info.filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download the full BIRD dev set.")
    parser.add_argument(
        "--out", type=Path, required=True, help="directory to extract into"
    )
    parser.add_argument(
        "--keep-zip",
        action="store_true",
        help="keep dev.zip next to the extracted files",
    )
    args = parser.parse_args(argv)
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / "dev.zip"

    print(f"Downloading {DEV_URL} ...", file=sys.stderr)
    actual = download(DEV_URL, archive)
    if actual != EXPECTED_SHA256:
        print(
            f"warning: SHA-256 is {actual}, expected {EXPECTED_SHA256}.\n"
            "The upstream release may have changed; compare with SOURCE.md before use.",
            file=sys.stderr,
        )
    extract(archive, out_dir)
    if not args.keep_zip:
        archive.unlink()
    print(f"Extracted BIRD dev into {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
