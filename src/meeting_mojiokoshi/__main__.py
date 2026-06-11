import os
import sys
import tempfile
import wave
from pathlib import Path


def run_self_check(full: bool = False) -> None:
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        os.environ.setdefault("PYSTRAY_BACKEND", "dummy")

    import tkinter

    import faster_whisper
    import numpy
    import platformdirs
    import pystray
    from PIL import Image, ImageDraw

    from meeting_mojiokoshi import audio, config, session, transcriber

    required = (
        tkinter,
        faster_whisper,
        numpy,
        platformdirs,
        pystray,
        Image,
        ImageDraw,
        audio,
        config,
        session,
        transcriber,
    )
    if any(module is None for module in required):
        raise SystemExit(1)

    if full:
        with tempfile.TemporaryDirectory(prefix="meeting-mojiokoshi-self-check-") as directory:
            root = Path(directory)
            audio_path = root / "silence.wav"
            transcript_path = root / "silence.txt"
            with wave.open(str(audio_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16_000)
                wav_file.writeframes(numpy.zeros(16_000, dtype=numpy.int16).tobytes())

            transcriber.prepare_model("tiny")
            result = transcriber.WhisperTranscriber(model_size="tiny", language="ja").transcribe(
                audio_path,
                transcript_path,
            )
            if not result.transcript_path.exists():
                raise SystemExit(1)


def main() -> None:
    self_check = os.environ.get("MEETING_MOJIOKOSHI_SELF_CHECK")
    if self_check in ("1", "full"):
        run_self_check(full=self_check == "full")
        return

    try:
        from meeting_mojiokoshi.app import main as app_main
    except ModuleNotFoundError as exc:
        if exc.name == "tkinter":
            if sys.platform == "win32":
                hint = (
                    "Windows では Python 公式インストーラー使用時に "
                    "「tcl/tk and IDLE」オプションを有効にしてください。"
                )
            elif sys.platform == "darwin":
                hint = (
                    "macOS では python.org の公式 Python を使うか、"
                    "Homebrew で `brew install python-tk` を実行してください。"
                )
            else:
                hint = (
                    "Linux では python3-tk などの OS パッケージをインストールしてください "
                    "（例: sudo apt-get install python3-tk）。"
                )
            raise SystemExit(
                "tkinter が見つかりません。\n" + hint
            ) from exc
        raise

    app_main()


if __name__ == "__main__":
    main()
