"""Secure local filesystem helpers for sensitive app data."""

from __future__ import annotations

import errno
import os
import re
import shutil
import stat
import tempfile
import time
from pathlib import Path
from typing import BinaryIO, TextIO

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600

_STALE_TRACK_AGE_SECONDS = 24 * 60 * 60
_TRACK_FILE_PATTERN = re.compile(
    r"^\.meeting_\d{8}_\d{6}(?:_\d+)?\.track-\d+\.wav$"
)


class SecureFsError(OSError):
    """Raised when a path is unsafe to create, replace, or delete."""


def is_posix() -> bool:
    return os.name == "posix"


def _chmod_private(path: Path, mode: int) -> None:
    if is_posix():
        os.chmod(path, mode)


def ensure_private_directory(path: Path, *, harden_existing: bool = True) -> Path:
    """Create or harden a directory to owner-only access on POSIX."""

    directory = Path(path)
    if directory.exists() or directory.is_symlink():
        if directory.is_symlink():
            raise SecureFsError(f"Refusing to use symlink directory: {directory}")
        if not directory.is_dir():
            raise SecureFsError(f"Expected a directory: {directory}")
        if harden_existing:
            _chmod_private(directory, PRIVATE_DIR_MODE)
        return directory

    parent = directory.parent
    if parent == directory:
        raise SecureFsError(f"Cannot create directory: {directory}")
    ensure_private_directory(parent, harden_existing=False)

    try:
        os.mkdir(
            directory,
            mode=PRIVATE_DIR_MODE if is_posix() else 0o777,
        )
    except FileExistsError:
        if directory.is_symlink() or not directory.is_dir():
            raise SecureFsError(f"Unsafe directory appeared during creation: {directory}")
    _chmod_private(directory, PRIVATE_DIR_MODE)
    return directory


def _exclusive_open_flags() -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if is_posix() and hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _replace_open_flags() -> int:
    flags = os.O_WRONLY | os.O_TRUNC
    if is_posix() and hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _validate_parent_directory(path: Path) -> None:
    parent = path.parent
    ensure_private_directory(parent, harden_existing=False)


def _validate_regular_output_target(path: Path, *, must_not_exist: bool) -> None:
    if path.exists() or path.is_symlink():
        if path.is_symlink():
            raise SecureFsError(f"Refusing to follow symlink: {path}")
        if must_not_exist:
            raise FileExistsError(errno.EEXIST, "File already exists", str(path))
        if not path.is_file():
            raise SecureFsError(f"Refusing to overwrite non-regular file: {path}")


def open_new_private_file(path: Path) -> int:
    """Open a new owner-only file without following symlinks."""

    target = Path(path)
    _validate_parent_directory(target)
    _validate_regular_output_target(target, must_not_exist=True)
    return os.open(
        target,
        _exclusive_open_flags(),
        PRIVATE_FILE_MODE if is_posix() else 0o666,
    )


def open_private_file_for_replace(path: Path) -> int:
    """Open an existing regular file for replacement, or create a new one."""

    target = Path(path)
    _validate_parent_directory(target)
    if target.exists() or target.is_symlink():
        _validate_regular_output_target(target, must_not_exist=False)
        return os.open(
            target,
            _replace_open_flags(),
            PRIVATE_FILE_MODE if is_posix() else 0o666,
        )
    return open_new_private_file(target)


def open_private_binary_writer(path: Path, *, exclusive: bool = True) -> BinaryIO:
    descriptor = (
        open_new_private_file(path)
        if exclusive
        else open_private_file_for_replace(path)
    )
    return os.fdopen(descriptor, "wb")


def open_private_text_writer(path: Path, *, exclusive: bool = True) -> TextIO:
    descriptor = (
        open_new_private_file(path)
        if exclusive
        else open_private_file_for_replace(path)
    )
    return os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")


def read_regular_text(path: Path) -> str:
    """Read a regular text file without following a final symlink."""

    target = Path(path)
    if target.is_symlink():
        raise SecureFsError(f"Refusing to read symlink: {target}")
    flags = os.O_RDONLY
    if is_posix() and hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags)
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise SecureFsError(f"Refusing to read non-regular file: {target}")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def atomic_write_private_text(path: Path, content: str) -> None:
    """Atomically write text to a destination directory with secure permissions."""

    destination = Path(path)
    _validate_parent_directory(destination)
    if destination.exists() or destination.is_symlink():
        _validate_regular_output_target(destination, must_not_exist=False)

    temporary_descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        text=True,
    )
    temporary = Path(temporary_path)
    try:
        with os.fdopen(temporary_descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _chmod_private(temporary, PRIVATE_FILE_MODE)
        os.replace(temporary, destination)
        _chmod_private(destination, PRIVATE_FILE_MODE)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def move_regular_file_no_replace(source: Path, destination: Path) -> None:
    """Move a regular file to a new path without replacing an existing entry."""

    src = Path(source)
    dst = Path(destination)
    if src.is_symlink() or not src.is_file():
        raise SecureFsError(f"Source is not a regular file: {src}")
    _validate_parent_directory(dst)
    _validate_regular_output_target(dst, must_not_exist=True)

    try:
        os.link(src, dst, follow_symlinks=False)
    except FileExistsError:
        raise
    except (NotImplementedError, OSError, TypeError) as exc:
        if isinstance(exc, OSError) and exc.errno not in {
            errno.EPERM,
            errno.EACCES,
            errno.EXDEV,
            errno.EOPNOTSUPP,
            errno.ENOTSUP,
            errno.EINVAL,
        }:
            raise

        read_flags = os.O_RDONLY
        if is_posix() and hasattr(os, "O_NOFOLLOW"):
            read_flags |= os.O_NOFOLLOW
        source_descriptor = os.open(src, read_flags)
        try:
            if not stat.S_ISREG(os.fstat(source_descriptor).st_mode):
                raise SecureFsError(f"Source is not a regular file: {src}")
            with os.fdopen(source_descriptor, "rb") as source_file:
                source_descriptor = -1
                try:
                    with open_private_binary_writer(dst, exclusive=True) as destination_file:
                        shutil.copyfileobj(source_file, destination_file)
                except Exception:
                    unlink_if_regular(dst)
                    raise
        finally:
            if source_descriptor >= 0:
                os.close(source_descriptor)
    if not unlink_if_regular(src):
        raise SecureFsError(f"Could not remove source file after move: {src}")
    _chmod_private(dst, PRIVATE_FILE_MODE)


def unlink_if_regular(path: Path) -> bool:
    """Delete a regular file owned by this process; never follow symlinks."""

    target = Path(path)
    if not target.exists() and not target.is_symlink():
        return False
    if target.is_symlink():
        return False
    if not target.is_file():
        return False
    if is_posix() and not _is_owned_by_current_user(target):
        return False
    target.unlink()
    return True


def _is_owned_by_current_user(path: Path) -> bool:
    file_stat = path.stat()
    return file_stat.st_uid == os.getuid()


def is_track_temp_file(path: Path) -> bool:
    return _TRACK_FILE_PATTERN.fullmatch(path.name) is not None


def clean_stale_track_files(directory: Path, *, max_age_seconds: int = _STALE_TRACK_AGE_SECONDS) -> int:
    """Remove stale hidden per-track WAV files created by this app."""

    root = Path(directory)
    if not root.is_dir() or root.is_symlink():
        return 0

    removed = 0
    current_time = time.time()
    for candidate in root.glob(".*.track-*.wav"):
        if not is_track_temp_file(candidate):
            continue
        if candidate.is_symlink() or not candidate.is_file():
            continue
        if is_posix() and not _is_owned_by_current_user(candidate):
            continue
        try:
            age_seconds = current_time - candidate.stat().st_mtime
        except OSError:
            continue
        if age_seconds < max_age_seconds:
            continue
        if unlink_if_regular(candidate):
            removed += 1
    return removed


def session_pair_is_available(audio_path: Path, transcript_path: Path) -> bool:
    for path in (audio_path, transcript_path):
        if path.is_symlink():
            return False
        if path.exists():
            return False
    return True
