from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from meeting_mojiokoshi.secure_fs import (
    clean_stale_track_files,
    ensure_private_directory,
    session_pair_is_available,
)


@dataclass(frozen=True)
class SessionPaths:
    base_name: str
    audio_path: Path
    transcript_path: Path


def create_session_paths(output_dir: Path, now: datetime | None = None) -> SessionPaths:
    root = ensure_private_directory(Path(output_dir))
    clean_stale_track_files(root)

    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    base_name = f"meeting_{timestamp}"
    candidate = base_name
    suffix = 1
    while True:
        audio_path = root / f"{candidate}.wav"
        transcript_path = root / f"{candidate}.txt"
        if session_pair_is_available(audio_path, transcript_path):
            return SessionPaths(
                base_name=candidate,
                audio_path=audio_path,
                transcript_path=transcript_path,
            )
        candidate = f"{base_name}_{suffix}"
        suffix += 1
