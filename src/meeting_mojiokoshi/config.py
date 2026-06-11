from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_config_dir

from meeting_mojiokoshi.secure_fs import (
    atomic_write_private_text,
    ensure_private_directory,
    read_regular_text,
)


AUTO_DEVICE = "__auto__"
DISABLED_DEVICE = "__disabled__"


@dataclass(frozen=True)
class AppSettings:
    output_dir: str
    meeting_device_name: str = AUTO_DEVICE
    microphone_device_name: str = AUTO_DEVICE
    model_size: str = "tiny"
    language: str = "ja"


def settings_path() -> Path:
    return Path(user_config_dir("MeetingMojiokoshi", "meeting-mojiokoshi")) / "settings.json"


def load_settings(default_output_dir: Path) -> AppSettings:
    path = settings_path()
    defaults = AppSettings(output_dir=str(default_output_dir))
    try:
        payload = json.loads(read_regular_text(path))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return defaults

    if not isinstance(payload, dict):
        return defaults

    values = asdict(defaults)
    for key in values:
        value = payload.get(key)
        if isinstance(value, str):
            values[key] = value
    return AppSettings(**values)


def save_settings(settings: AppSettings) -> None:
    path = settings_path()
    ensure_private_directory(path.parent)
    content = json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n"
    atomic_write_private_text(path, content)
