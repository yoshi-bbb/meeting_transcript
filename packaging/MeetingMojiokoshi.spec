# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files


# UPX has known compatibility issues with macOS (especially arm64) and
# can interfere with code signing / notarization. Disable on darwin.
use_upx = sys.platform != "darwin"


project_root = Path.cwd()
entry_point = project_root / "src" / "meeting_mojiokoshi" / "__main__.py"

if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    os.environ.setdefault("PYSTRAY_BACKEND", "dummy")

datas = []
binaries = []
hiddenimports = []

for package_name in (
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "hf_xet",
    "av",
    "pystray",
    "PIL",
):
    try:
        package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    except Exception:
        continue
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

soundcard_backends = {
    "linux": "soundcard.pulseaudio",
    "darwin": "soundcard.coreaudio",
    "win32": "soundcard.mediafoundation",
}
soundcard_backend = soundcard_backends.get(sys.platform)
if soundcard_backend:
    hiddenimports += ["soundcard", soundcard_backend]
datas += collect_data_files("soundcard", includes=["*.py.h"])
excluded_soundcard_backends = [
    backend for platform, backend in soundcard_backends.items() if platform != sys.platform
]

# Ensure tkinter is collected for the self-check (run_self_check with full=True)
# This is critical for the frozen binary on macOS (and helps on other platforms)
# The self-check imports tkinter at the top of the function and is used in CI smoke tests.
hiddenimports += ["tkinter"]
try:
    datas += collect_data_files("tkinter")
except Exception:
    pass  # tkinter data collection is best-effort; PyInstaller hooks usually handle it

a = Analysis(
    [str(entry_point)],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_soundcard_backends,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

common_exe_options = dict(
    name="MeetingMojiokoshi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=use_upx,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **common_exe_options,
    )
    collection = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=use_upx,
        upx_exclude=[],
        name="MeetingMojiokoshi",
    )
    app = BUNDLE(
        collection,
        name="MeetingMojiokoshi.app",
        icon=None,
        bundle_identifier="app.meeting-mojiokoshi.desktop",
        version="0.2.0",
        info_plist={
            "CFBundleDisplayName": "Meeting Mojiokoshi",
            "NSMicrophoneUsageDescription": "会議音声とマイクを録音して文字起こしするために使用します。",
            "NSHighResolutionCapable": True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        **common_exe_options,
    )
