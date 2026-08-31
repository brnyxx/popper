#!/usr/bin/env python3
"""Create a deterministic SHA256SUMS file using the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Sequence


class ChecksumBuildError(ValueError):
    """An input is missing, unsafe, duplicated, or conflicts with the output."""


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build(output: Path, inputs: Sequence[Path]) -> tuple[str, ...]:
    target = output.expanduser().resolve()
    records: dict[str, Path] = {}
    for raw in inputs:
        path = raw.expanduser().resolve()
        name = path.name
        if (
            not path.is_file()
            or path.is_symlink()
            or name in {"", ".", ".."}
            or "\\" in name
            or ":" in name
        ):
            raise ChecksumBuildError(f"INVALID_INPUT:{raw}")
        if path == target:
            raise ChecksumBuildError(f"OUTPUT_IS_INPUT:{raw}")
        if name in records:
            raise ChecksumBuildError(f"DUPLICATE_BASENAME:{name}")
        records[name] = path
    if not records:
        raise ChecksumBuildError("NO_INPUTS")

    lines = tuple(f"{_digest(records[name])}  {name}" for name in sorted(records))
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    for line in build(args.output, args.inputs):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
