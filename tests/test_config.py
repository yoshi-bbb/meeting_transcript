from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from meeting_mojiokoshi import config
from meeting_mojiokoshi.config import AppSettings


def test_settings_round_trip(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(config, "settings_path", lambda: path)
    expected = AppSettings(
        output_dir="/tmp/meetings",
        meeting_device_name="System Audio",
        microphone_device_name="Microphone",
        model_size="base",
        language="ja",
    )

    config.save_settings(expected)

    assert config.load_settings(Path("/fallback")) == expected


def test_invalid_settings_use_defaults(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(config, "settings_path", lambda: path)

    loaded = config.load_settings(Path("/fallback"))

    assert loaded.output_dir == str(Path("/fallback"))
    assert loaded.model_size == "tiny"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission checks")
def test_save_settings_sets_owner_only_permissions(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(config, "settings_path", lambda: path)
    config.save_settings(AppSettings(output_dir=str(tmp_path / "output")))
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_load_settings_does_not_follow_symlink(tmp_path: Path, monkeypatch) -> None:
    real_path = tmp_path / "real.json"
    real_path.write_text('{"output_dir": "/private"}', encoding="utf-8")
    path = tmp_path / "settings.json"
    path.symlink_to(real_path)
    monkeypatch.setattr(config, "settings_path", lambda: path)

    loaded = config.load_settings(Path("/fallback"))

    assert loaded.output_dir == "/fallback"
