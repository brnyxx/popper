#!/usr/bin/env python3
"""Normalize Python sdists into deterministic, fail-closed tar.gz archives."""

from __future__ import annotations

import argparse
import copy
import gzip
import io
import os
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Sequence

DEFAULT_EPOCH = 1767225600


class SdistNormalizationError(ValueError):
    """The source archive is malformed or contains an unsafe member."""


def _safe_name(name: str) -> str:
    path = PurePosixPath(name)
    canonical = path.as_posix().rstrip("/")
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or canonical != name.rstrip("/")
    ):
        raise SdistNormalizationError(f"UNSAFE_MEMBER:{name}")
    return canonical


def normalize(path: Path, *, epoch: int = DEFAULT_EPOCH) -> None:
    source = path.expanduser().resolve()
    try:
        with tarfile.open(source, "r:gz") as archive:
            members = archive.getmembers()
            payloads: dict[str, bytes] = {}
            for member in members:
                if not member.isfile():
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    raise SdistNormalizationError(f"UNREADABLE_MEMBER:{member.name}")
                payloads[member.name] = stream.read()
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise SdistNormalizationError(f"INVALID_SDIST:{source}") from exc

    normalized: list[tarfile.TarInfo] = []
    normalized_payloads: dict[str, bytes] = {}
    seen: set[str] = set()
    for original in members:
        name = _safe_name(original.name)
        if name in seen:
            raise SdistNormalizationError(f"DUPLICATE_MEMBER:{name}")
        seen.add(name)
        if not (original.isfile() or original.isdir()):
            raise SdistNormalizationError(f"UNSUPPORTED_MEMBER:{name}")
        member = copy.copy(original)
        member.name = name
        member.uid = 0
        member.gid = 0
        member.uname = ""
        member.gname = ""
        member.mtime = epoch
        member.mode = 0o644 if member.isfile() else 0o755
        member.pax_headers = {}
        if member.isdir():
            member.size = 0
        else:
            normalized_payloads[name] = payloads[original.name]
        normalized.append(member)

    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=buffer, compresslevel=9, mtime=epoch
    ) as compressed:
        with tarfile.open(
            fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT
        ) as output:
            for member in sorted(normalized, key=lambda item: item.name):
                data = (
                    io.BytesIO(normalized_payloads[member.name])
                    if member.isfile()
                    else None
                )
                output.addfile(member, data)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{source.name}.", dir=source.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(buffer.getvalue())
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, source)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdists", nargs="+", type=Path)
    parser.add_argument(
        "--epoch",
        type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_EPOCH)),
    )
    args = parser.parse_args(argv)
    for sdist in args.sdists:
        normalize(sdist, epoch=args.epoch)
        print(f"normalized {sdist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
