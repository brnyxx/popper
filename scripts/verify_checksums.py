#!/usr/bin/env python3
"""Verify a SHA256SUMS file with only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from typing import Sequence

CHECKSUM_LINE = re.compile(r"^(?P<digest>[0-9a-f]{64})  (?P<name>[^\r\n]+)$")


class ChecksumError(ValueError):
    """Checksum input is unsafe, malformed, incomplete, or mismatched."""


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify(
    checksum_file: Path, *, only: Sequence[str] | None = None
) -> tuple[str, ...]:
    source = checksum_file.expanduser().resolve()
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ChecksumError(f"CHECKSUM_FILE_UNREADABLE:{source}") from exc
    if not lines:
        raise ChecksumError("CHECKSUM_FILE_EMPTY")

    records: dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        match = CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise ChecksumError(f"MALFORMED_LINE:{number}")
        name = match.group("name")
        relative = Path(name)
        if (
            relative.is_absolute()
            or len(relative.parts) != 1
            or name in {".", ".."}
            or "\\" in name
            or ":" in name
        ):
            raise ChecksumError(f"UNSAFE_PATH:{number}:{name}")
        if name in records:
            raise ChecksumError(f"DUPLICATE_PATH:{number}:{name}")
        records[name] = match.group("digest")

    selected: set[str] | None = None
    if only is not None:
        selected = set()
        for name in only:
            relative = Path(name)
            if (
                relative.is_absolute()
                or len(relative.parts) != 1
                or name in {"", ".", ".."}
                or "\\" in name
                or ":" in name
            ):
                raise ChecksumError(f"UNSAFE_SELECTION:{name}")
            if name in selected:
                raise ChecksumError(f"DUPLICATE_SELECTION:{name}")
            if name not in records:
                raise ChecksumError(f"MISSING_CHECKSUM_ENTRY:{name}")
            selected.add(name)
        if not selected:
            raise ChecksumError("EMPTY_SELECTION")

    verified: list[str] = []
    for name, expected in records.items():
        if selected is not None and name not in selected:
            continue
        target = source.parent / name
        if not target.is_file() or target.is_symlink():
            raise ChecksumError(f"MISSING_FILE:{name}")
        actual = _digest(target)
        if actual != expected:
            raise ChecksumError(f"CHECKSUM_MISMATCH:{name}")
        verified.append(name)
    return tuple(verified)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checksum_file", type=Path)
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="FILE",
        help="verify only these named release assets while still parsing the full list",
    )
    args = parser.parse_args()
    for name in verify(args.checksum_file, only=args.only):
        print(f"{name}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
