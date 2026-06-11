from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def executable_path(project_root: Path) -> Path:
    if sys.platform == "win32":
        return project_root / "dist" / "MeetingMojiokoshi.exe"
    if sys.platform == "darwin":
        return (
            project_root
            / "dist"
            / "MeetingMojiokoshi.app"
            / "Contents"
            / "MacOS"
            / "MeetingMojiokoshi"
        )
    return project_root / "dist" / "MeetingMojiokoshi"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Download tiny model and run CPU transcription")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    executable = executable_path(project_root)
    if not executable.exists():
        raise SystemExit(f"Built executable was not found: {executable}")

    # Ensure the executable is runnable (especially important on macOS CI after PyInstaller)
    if sys.platform == "darwin":
        try:
            executable.chmod(0o755)
        except Exception:
            pass

    environment = os.environ.copy()
    environment["MEETING_MOJIOKOSHI_SELF_CHECK"] = "full" if args.full else "1"
    timeout_seconds = 600 if args.full else 60
    try:
        completed = subprocess.run(
            [str(executable)],
            cwd=project_root,
            env=environment,
            timeout=timeout_seconds,
            check=False,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        print("=== STDOUT ===")
        print(exc.stdout or "")
        print("=== STDERR ===")
        print(exc.stderr or "")
        raise SystemExit(f"Desktop self-check timed out after {timeout_seconds}s") from exc

    if completed.returncode != 0:
        print("=== STDOUT ===")
        print(completed.stdout or "")
        print("=== STDERR ===")
        print(completed.stderr or "")
        raise SystemExit(f"Desktop self-check failed with exit code {completed.returncode}")
    mode = "full" if args.full else "basic"
    print(f"Desktop {mode} self-check passed: {executable}")


if __name__ == "__main__":
    main()
