from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    spec_file = project_root / "packaging" / "MeetingMojiokoshi.spec"
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(spec_file),
        ],
        cwd=project_root,
    )


if __name__ == "__main__":
    main()

