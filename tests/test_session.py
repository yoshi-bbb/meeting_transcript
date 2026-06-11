from datetime import datetime
from pathlib import Path

from meeting_mojiokoshi.session import create_session_paths


def test_create_session_paths_avoids_existing_files(tmp_path: Path) -> None:
    now = datetime(2026, 6, 8, 12, 34, 56)
    (tmp_path / "meeting_20260608_123456.wav").touch()
    (tmp_path / "meeting_20260608_123456_1.txt").touch()

    paths = create_session_paths(tmp_path, now=now)

    assert paths.base_name == "meeting_20260608_123456_2"
    assert paths.audio_path.name == "meeting_20260608_123456_2.wav"
    assert paths.transcript_path.name == "meeting_20260608_123456_2.txt"


def test_create_session_paths_skips_symlink_collision(tmp_path: Path) -> None:
    now = datetime(2026, 6, 8, 12, 34, 56)
    real_file = tmp_path / "real.wav"
    real_file.write_bytes(b"wav")
    (tmp_path / "meeting_20260608_123456.wav").symlink_to(real_file)

    paths = create_session_paths(tmp_path, now=now)

    assert paths.base_name == "meeting_20260608_123456_1"
    assert real_file.read_bytes() == b"wav"
