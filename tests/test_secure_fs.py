from __future__ import annotations

import os
import stat
import time
from pathlib import Path

import pytest

from meeting_mojiokoshi.secure_fs import (
    SecureFsError,
    atomic_write_private_text,
    clean_stale_track_files,
    ensure_private_directory,
    is_track_temp_file,
    move_regular_file_no_replace,
    open_new_private_file,
    unlink_if_regular,
)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission checks")
def test_ensure_private_directory_sets_owner_only_mode(tmp_path: Path) -> None:
    directory = tmp_path / "nested" / "private"
    ensure_private_directory(directory)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission checks")
def test_atomic_write_private_text_sets_owner_only_mode(tmp_path: Path) -> None:
    destination = tmp_path / "settings.json"
    atomic_write_private_text(destination, '{"ok": true}\n')
    assert destination.read_text(encoding="utf-8") == '{"ok": true}\n'
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600


def test_open_new_private_file_rejects_existing_symlink(tmp_path: Path) -> None:
    target = tmp_path / "secret.wav"
    real_file = tmp_path / "real.wav"
    real_file.write_bytes(b"data")
    target.symlink_to(real_file)

    with pytest.raises(SecureFsError):
        open_new_private_file(target)


def test_atomic_write_private_text_rejects_existing_symlink(tmp_path: Path) -> None:
    destination = tmp_path / "settings.json"
    real_file = tmp_path / "real.json"
    real_file.write_text("{}", encoding="utf-8")
    destination.symlink_to(real_file)

    with pytest.raises(SecureFsError):
        atomic_write_private_text(destination, "{}\n")


def test_unlink_if_regular_does_not_follow_symlink(tmp_path: Path) -> None:
    real_file = tmp_path / "real.wav"
    real_file.write_bytes(b"data")
    link = tmp_path / "link.wav"
    link.symlink_to(real_file)

    assert unlink_if_regular(link) is False
    assert real_file.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX ownership checks")
def test_clean_stale_track_files_removes_old_app_tracks(tmp_path: Path) -> None:
    stale_track = tmp_path / ".meeting_20260101_120000.track-0.wav"
    stale_track.write_bytes(b"wav")
    old_time = time.time() - (25 * 60 * 60)
    os.utime(stale_track, (old_time, old_time))

    removed = clean_stale_track_files(tmp_path, max_age_seconds=60)

    assert removed == 1
    assert not stale_track.exists()


def test_clean_stale_track_files_preserves_similar_unrelated_file(tmp_path: Path) -> None:
    unrelated = tmp_path / ".personal.track-0.wav"
    unrelated.write_bytes(b"wav")
    old_time = time.time() - (25 * 60 * 60)
    os.utime(unrelated, (old_time, old_time))

    assert clean_stale_track_files(tmp_path, max_age_seconds=60) == 0
    assert unrelated.exists()


def test_is_track_temp_file_matches_hidden_track_names() -> None:
    assert is_track_temp_file(Path(".meeting_20260101_120000.track-0.wav"))
    assert is_track_temp_file(Path(".meeting_20260101_120000_2.track-1.wav"))
    assert not is_track_temp_file(Path("meeting_20260101_120000.wav"))
    assert not is_track_temp_file(Path(".personal.track-0.wav"))


def test_move_regular_file_no_replace_refuses_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / ".meeting_20260101_120000.track-0.wav"
    destination = tmp_path / "meeting_20260101_120000.wav"
    source.write_bytes(b"recording")
    destination.write_bytes(b"unrelated")

    with pytest.raises(FileExistsError):
        move_regular_file_no_replace(source, destination)

    assert source.read_bytes() == b"recording"
    assert destination.read_bytes() == b"unrelated"
