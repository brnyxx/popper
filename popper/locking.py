"""프로세스 간 파일 잠금 경계.

같은 소유 디렉토리를 사용하는 모든 CLI/웹 세션은 하나의 재진입 가능한
잠금을 공유한다. 파일 잠금 구현은 Windows/macOS/Linux 차이를 검증된
``filelock`` 라이브러리에 맡긴다.
"""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from filelock import FileLock

LOCK_TIMEOUT_SECONDS = 60

_registry: dict[Path, FileLock] = {}
_registry_guard = Lock()


def lock_for_path(path: Path | str) -> FileLock:
    """정규화된 잠금 파일마다 프로세스 내 FileLock 인스턴스를 하나만 만든다."""
    lock_path = Path(path).expanduser().resolve()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with _registry_guard:
        lock = _registry.get(lock_path)
        if lock is None:
            lock = FileLock(str(lock_path), timeout=LOCK_TIMEOUT_SECONDS)
            _registry[lock_path] = lock
        return lock


def base_lock(base_dir: Path | str) -> FileLock:
    """이벤트와 파생 산출물 전체를 직렬화하는 소유 디렉토리 잠금."""
    base = Path(base_dir).expanduser().resolve()
    return lock_for_path(base.parent / f".{base.name}.popper.lock")


def target_lock(target: Path | str) -> FileLock:
    """소유 디렉토리 밖 단일 사용자 파일을 보호하는 형제 잠금."""
    path = Path(target).expanduser().resolve()
    return lock_for_path(path.with_name(f".{path.name}.popper.lock"))
