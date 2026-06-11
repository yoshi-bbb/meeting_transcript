from __future__ import annotations

import hashlib
import io
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from meeting_mojiokoshi import __version__


def normalized_architecture() -> str:
    machine = platform.machine().lower()
    return {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine, machine or "unknown")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_windows(project_root: Path, release_dir: Path, base_name: str) -> Path:
    executable = project_root / "dist" / "MeetingMojiokoshi.exe"
    if not executable.exists():
        raise FileNotFoundError(executable)
    archive = release_dir / f"{base_name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(executable, executable.name)
        zip_file.write(project_root / "README.md", "README.md")
        zip_file.write(project_root / "LICENSE", "LICENSE")
    return archive


def package_macos(project_root: Path, release_dir: Path, base_name: str) -> Path:
    app_bundle = project_root / "dist" / "MeetingMojiokoshi.app"
    if not app_bundle.exists():
        raise FileNotFoundError(app_bundle)
    archive = release_dir / f"{base_name}.zip"
    ditto = shutil.which("ditto")
    if ditto:
        subprocess.check_call(
            [
                ditto,
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(app_bundle),
                str(archive),
            ]
        )
    else:
        shutil.make_archive(str(archive.with_suffix("")), "zip", app_bundle.parent, app_bundle.name)
    with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(project_root / "README.md", "README.md")
        zip_file.write(project_root / "LICENSE", "LICENSE")
    return archive


def package_linux(project_root: Path, release_dir: Path, base_name: str) -> Path:
    executable = project_root / "dist" / "MeetingMojiokoshi"
    if not executable.exists():
        raise FileNotFoundError(executable)

    # Generate a .desktop file so users can easily add it to their application menu
    # and have better desktop integration (icon, name, categories).
    # Users still need to adjust the Exec= path after extracting, or install the binary
    # to a standard location (e.g. ~/.local/bin).
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Meeting Mojiokoshi
Comment=オンラインミーティングの音声を録音し、CPU版Whisperで文字起こし
Exec={executable.name}
Icon=applications-multimedia
Terminal=false
Categories=AudioVideo;Audio;Utility;
StartupNotify=true
"""

    archive = release_dir / f"{base_name}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar_file:
        # Ensure the binary is marked executable (0o755) in the archive.
        # This helps when users extract it; many file managers still require
        # an explicit "Allow executing" or chmod, but it's better than nothing.
        tarinfo = tarfile.TarInfo(name=executable.name)
        tarinfo.mode = 0o755
        tarinfo.size = executable.stat().st_size
        with executable.open("rb") as f:
            tar_file.addfile(tarinfo, f)

        tar_file.add(project_root / "README.md", arcname="README.md")
        tar_file.add(project_root / "LICENSE", arcname="LICENSE")

        # Add the .desktop file
        desktop_tarinfo = tarfile.TarInfo(name="MeetingMojiokoshi.desktop")
        desktop_data = desktop_content.encode("utf-8")
        desktop_tarinfo.size = len(desktop_data)
        desktop_tarinfo.mode = 0o644
        tar_file.addfile(desktop_tarinfo, io.BytesIO(desktop_data))

    return archive


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    release_dir = project_root / "release"
    release_dir.mkdir(parents=True, exist_ok=True)

    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    base_name = f"MeetingMojiokoshi-{__version__}-{system}-{normalized_architecture()}"
    if sys.platform == "win32":
        archive = package_windows(project_root, release_dir, base_name)
    elif sys.platform == "darwin":
        archive = package_macos(project_root, release_dir, base_name)
    else:
        archive = package_linux(project_root, release_dir, base_name)

    checksum_path = archive.with_name(f"{archive.name}.sha256")
    checksum_path.write_text(f"{sha256(archive)}  {archive.name}\n", encoding="ascii")
    print(archive)
    print(checksum_path)


if __name__ == "__main__":
    main()
