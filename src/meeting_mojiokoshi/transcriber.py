from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from platformdirs import user_cache_dir

from meeting_mojiokoshi.models import (
    ALLOWED_MODEL_SIZES,
    download_trusted_model,
    resolve_trusted_model,
)
from meeting_mojiokoshi.secure_fs import ensure_private_directory, open_private_text_writer


ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class TranscriptionResult:
    audio_path: Path
    transcript_path: Path
    language: str
    duration_seconds: float


def default_model_cache_dir() -> Path:
    configured = os.environ.get("MEETING_MOJIOKOSHI_MODEL_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(user_cache_dir("MeetingMojiokoshi", "meeting-mojiokoshi")) / "models"


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def prepare_model(
    model_size: str,
    model_cache_dir: Path | None = None,
    progress: ProgressCallback | None = None,
    retries: int = 3,
) -> Path:
    trusted = resolve_trusted_model(model_size)
    cache_dir = ensure_private_directory(model_cache_dir or default_model_cache_dir())
    if progress:
        progress(f"Whisper モデルを準備中: {trusted.size}")

    last_error: Exception | None = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            model_path = download_trusted_model(
                trusted,
                cache_dir=cache_dir,
            )
            break
        except Exception as exc:
            last_error = exc
            if attempt >= retries or not _is_retryable_download_error(exc):
                raise
            delay_seconds = min(60, 10 * attempt)
            if progress:
                progress(
                    f"モデル取得を再試行します ({attempt}/{retries}): "
                    f"{delay_seconds} 秒後"
                )
            time.sleep(delay_seconds)
    else:
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Failed to prepare model: {trusted.size}")

    if progress:
        progress(f"モデルの準備が完了しました: {trusted.size}")
    return model_path


def _is_retryable_download_error(exc: Exception) -> bool:
    message = f"{type(exc).__name__}: {exc}"
    retryable_markers = (
        "429",
        "Too Many Requests",
        "ConnectionError",
        "ConnectTimeout",
        "ReadTimeout",
        "HfHubHTTPError",
        "LocalEntryNotFoundError",
    )
    return any(marker in message for marker in retryable_markers)


def model_is_available(model_size: str, model_cache_dir: Path | None = None) -> bool:
    trusted = resolve_trusted_model(model_size)
    cache_dir = model_cache_dir or default_model_cache_dir()
    try:
        download_trusted_model(
            trusted,
            cache_dir=Path(cache_dir),
            local_files_only=True,
        )
    except (FileNotFoundError, OSError, ValueError):
        return False
    return True


class WhisperTranscriber:
    def __init__(
        self,
        model_size: str = "tiny",
        language: str | None = "ja",
        model_cache_dir: Path | None = None,
    ) -> None:
        if model_size not in ALLOWED_MODEL_SIZES:
            allowed = ", ".join(sorted(ALLOWED_MODEL_SIZES))
            raise ValueError(
                f"Unsupported model size '{model_size}'. Allowed values: {allowed}"
            )
        self.trusted_model = resolve_trusted_model(model_size)
        self.model_size = self.trusted_model.size
        self.language = language.strip() if language else None
        self.model_cache_dir = model_cache_dir or default_model_cache_dir()

    def transcribe(
        self,
        audio_path: Path,
        transcript_path: Path,
        progress: ProgressCallback | None = None,
    ) -> TranscriptionResult:
        audio_path = Path(audio_path)
        transcript_path = Path(transcript_path)
        ensure_private_directory(transcript_path.parent)
        ensure_private_directory(self.model_cache_dir)

        self._progress(progress, f"Whisper モデルを読み込み中: {self.model_size}")
        from faster_whisper import WhisperModel

        model_path = prepare_model(
            self.model_size,
            model_cache_dir=self.model_cache_dir,
            progress=progress,
        )
        model = WhisperModel(
            str(model_path),
            device="cpu",
            compute_type="int8",
        )

        self._progress(progress, "文字起こしを開始しました。")
        segments, info = model.transcribe(
            str(audio_path),
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 700},
        )

        detected_language = getattr(info, "language", None) or self.language or "unknown"
        duration = float(getattr(info, "duration", 0.0) or 0.0)

        with open_private_text_writer(transcript_path, exclusive=True) as file:
            file.write("# Meeting Mojiokoshi Transcript\n\n")
            file.write(f"- audio: {audio_path.name}\n")
            file.write(f"- model: {self.model_size}\n")
            file.write(f"- language: {detected_language}\n")
            if duration:
                file.write(f"- duration: {format_timestamp(duration)}\n")
            file.write("\n")

            last_reported = -1
            for segment in segments:
                start = format_timestamp(float(segment.start))
                end = format_timestamp(float(segment.end))
                text = segment.text.strip()
                if text:
                    file.write(f"[{start} --> {end}] {text}\n")

                current_minute = int(segment.end // 60)
                if current_minute != last_reported:
                    last_reported = current_minute
                    self._progress(progress, f"文字起こし中: {format_timestamp(float(segment.end))}")

        self._progress(progress, f"文字起こしを保存しました: {transcript_path.name}")
        return TranscriptionResult(
            audio_path=audio_path,
            transcript_path=transcript_path,
            language=detected_language,
            duration_seconds=duration,
        )

    @staticmethod
    def _progress(progress: ProgressCallback | None, message: str) -> None:
        if progress:
            progress(message)
