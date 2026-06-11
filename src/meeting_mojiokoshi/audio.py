from __future__ import annotations

import sys
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from meeting_mojiokoshi.secure_fs import (
    clean_stale_track_files,
    ensure_private_directory,
    is_track_temp_file,
    move_regular_file_no_replace,
    open_private_binary_writer,
    unlink_if_regular,
)


SAMPLE_RATE = 16_000
CHANNELS = 1
CHUNK_SECONDS = 0.5
MIX_CHUNK_FRAMES = 16_000
_SOUNDCARD_MODULE: Any | None = None


class RecordingError(RuntimeError):
    """Raised when recording cannot start or complete."""


@dataclass(frozen=True)
class AudioDevice:
    index: int
    backend_id: Any
    name: str
    label: str
    is_loopback_like: bool


def _soundcard() -> Any:
    global _SOUNDCARD_MODULE
    if _SOUNDCARD_MODULE is None:
        # soundcard's PulseAudio backend expects a user argument when it
        # infers the process name in some non-interactive launch modes.
        if len(sys.argv) < 2:
            sys.argv.append("meeting-mojiokoshi")
        import soundcard as soundcard_module

        _SOUNDCARD_MODULE = soundcard_module
    return _SOUNDCARD_MODULE


def _all_microphones() -> list[Any]:
    sc = _soundcard()
    try:
        return list(sc.all_microphones(include_loopback=True))
    except TypeError:
        return list(sc.all_microphones())


def _get_microphone(device_id: Any) -> Any:
    sc = _soundcard()
    try:
        return sc.get_microphone(device_id, include_loopback=True)
    except TypeError:
        return sc.get_microphone(device_id)


def list_audio_inputs() -> list[AudioDevice]:
    devices = []
    for index, microphone in enumerate(_all_microphones()):
        name = getattr(microphone, "name", None) or f"Input {index}"
        lowered = name.lower()
        is_loopback_like = bool(getattr(microphone, "isloopback", False)) or any(
            keyword in lowered
            for keyword in (
                "loopback",
                "monitor",
                "stereo mix",
                "what u hear",
                "blackhole",
                "black hole",
                "soundflower",
                "aggregate",
                "multi-output",
                "voicemeeter",
                "vb-audio",
                "vb cable",
            )
        )
        suffix = " / system audio" if is_loopback_like else ""
        devices.append(
            AudioDevice(
                index=index,
                backend_id=getattr(microphone, "id", index),
                name=name,
                label=f"{index}: {name}{suffix}",
                is_loopback_like=is_loopback_like,
            )
        )
    return devices


def preferred_device_index(devices: Sequence[AudioDevice]) -> int | None:
    for device in devices:
        if device.is_loopback_like:
            return device.index
    return devices[0].index if devices else None


def preferred_microphone_index(devices: Sequence[AudioDevice]) -> int | None:
    for device in devices:
        if not device.is_loopback_like:
            return device.index
    return None


class AudioRecorder:
    """Records one backend input into a temporary mono PCM WAV file."""

    def __init__(
        self,
        device_id: Any,
        output_path: Path,
        samplerate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        chunk_seconds: float = CHUNK_SECONDS,
        start_gate: threading.Event | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.device_id = device_id
        self.output_path = Path(output_path)
        self.samplerate = samplerate
        self.channels = channels
        self.chunk_seconds = chunk_seconds
        self.on_error = on_error

        self._stop_event = threading.Event()
        self._start_gate = start_gate or threading.Event()
        self._owns_start_gate = start_gate is None
        self._ready_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.error: Exception | None = None
        self.frame_count = 0

    @property
    def is_recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set()

    def start(self, startup_timeout: float = 10.0) -> None:
        if self._thread and self._thread.is_alive():
            raise RecordingError("Recording is already running.")

        ensure_private_directory(self.output_path.parent)
        self._stop_event.clear()
        self._ready_event.clear()
        self.error = None
        self.frame_count = 0
        self._thread = threading.Thread(target=self._record_loop, name="audio-recorder", daemon=True)
        self._thread.start()

        if not self._ready_event.wait(timeout=startup_timeout):
            self.stop()
            raise RecordingError("録音デバイスの開始がタイムアウトしました。")
        if self.error:
            raise RecordingError(str(self.error)) from self.error
        if self._owns_start_gate:
            self._start_gate.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._start_gate.set()

    def join(self, timeout: float | None = None, raise_on_error: bool = True) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                raise RecordingError("録音デバイスを停止できませんでした。")
        if raise_on_error and self.error:
            raise RecordingError(str(self.error)) from self.error

    def _record_loop(self) -> None:
        try:
            microphone = _get_microphone(self.device_id)
            if microphone is None:
                raise RecordingError("選択された録音デバイスが見つかりません。")

            chunk_frames = max(1, int(self.samplerate * self.chunk_seconds))
            with open_private_binary_writer(self.output_path, exclusive=True) as raw_file:
                with wave.open(raw_file, "wb") as wav_file:
                    wav_file.setnchannels(self.channels)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(self.samplerate)

                    with microphone.recorder(samplerate=self.samplerate, channels=self.channels) as recorder:
                        self._ready_event.set()
                        self._start_gate.wait()
                        while not self._stop_event.is_set():
                            data = recorder.record(numframes=chunk_frames)
                            pcm = self._float_audio_to_int16(data)
                            wav_file.writeframes(pcm.tobytes())
                            self.frame_count += len(pcm)
        except Exception as exc:  # noqa: BLE001 - backend details are shown in the GUI.
            self.error = exc
            if self.on_error:
                self.on_error(str(exc))
        finally:
            self._ready_event.set()

    @staticmethod
    def _float_audio_to_int16(data: np.ndarray) -> np.ndarray:
        if data.ndim == 1:
            normalized = data
        else:
            normalized = data[:, 0]
        clipped = np.clip(normalized, -1.0, 1.0)
        return (clipped * 32767.0).astype(np.int16)


class MeetingRecorder:
    """Synchronously records one or more inputs and creates a mixed WAV.

    Temporary per-track files are hidden ``.meeting_*.track-*.wav`` files in the
    output directory. They are removed on normal completion or failure, but an
    abrupt process termination can leave stale hidden tracks behind. The app
    removes stale app-owned track files older than 24 hours when starting a new
    session.
    """

    def __init__(
        self,
        devices: Sequence[AudioDevice],
        output_path: Path,
        samplerate: int = SAMPLE_RATE,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        if not devices:
            raise RecordingError("録音デバイスを1つ以上選択してください。")

        unique_devices: list[AudioDevice] = []
        seen_ids: set[str] = set()
        for device in devices:
            identity = repr(device.backend_id)
            if identity not in seen_ids:
                seen_ids.add(identity)
                unique_devices.append(device)

        self.devices = unique_devices
        self.output_path = Path(output_path)
        self.samplerate = samplerate
        self.on_error = on_error
        self.warnings: list[str] = []

        self._start_gate = threading.Event()
        self._recorders: list[AudioRecorder] = []
        self._error_reported = False
        self.frame_count = 0

    @property
    def is_recording(self) -> bool:
        return any(recorder.is_recording for recorder in self._recorders)

    def start(self) -> None:
        ensure_private_directory(self.output_path.parent)
        clean_stale_track_files(self.output_path.parent)
        self._start_gate.clear()
        self._recorders = []
        self.warnings = []
        self.frame_count = 0
        self._error_reported = False

        try:
            for track_number, device in enumerate(self.devices):
                track_path = self._track_path(track_number)
                recorder = AudioRecorder(
                    device_id=device.backend_id,
                    output_path=track_path,
                    samplerate=self.samplerate,
                    start_gate=self._start_gate,
                    on_error=lambda message, name=device.name: self._handle_track_error(name, message),
                )
                recorder.start()
                self._recorders.append(recorder)
            self._start_gate.set()
        except Exception:
            self.stop()
            for recorder in self._recorders:
                recorder.join(timeout=3, raise_on_error=False)
            self._cleanup_tracks()
            raise

    def stop(self) -> None:
        self._start_gate.set()
        for recorder in self._recorders:
            recorder.stop()

    def join(self, timeout: float | None = None) -> None:
        for recorder in self._recorders:
            recorder.join(timeout=timeout, raise_on_error=False)
            if recorder.error:
                self.warnings.append(str(recorder.error))

        usable_tracks = [
            recorder.output_path
            for recorder in self._recorders
            if recorder.frame_count > 0 and recorder.output_path.exists()
        ]
        if not usable_tracks:
            self._cleanup_tracks()
            errors = "; ".join(dict.fromkeys(self.warnings))
            raise RecordingError(errors or "録音された音声がありません。")

        try:
            if len(usable_tracks) == 1:
                move_regular_file_no_replace(usable_tracks[0], self.output_path)
            else:
                mix_wav_files(usable_tracks, self.output_path)
            with wave.open(str(self.output_path), "rb") as wav_file:
                self.frame_count = wav_file.getnframes()
        finally:
            self._cleanup_tracks()

    def _track_path(self, track_number: int) -> Path:
        return self.output_path.with_name(f".{self.output_path.stem}.track-{track_number}.wav")

    def _cleanup_tracks(self) -> None:
        for track_number in range(len(self.devices)):
            track_path = self._track_path(track_number)
            if is_track_temp_file(track_path):
                unlink_if_regular(track_path)

    def _handle_track_error(self, device_name: str, message: str) -> None:
        warning = f"{device_name}: {message}"
        self.warnings.append(warning)
        self.stop()
        if self.on_error and not self._error_reported:
            self._error_reported = True
            self.on_error(warning)


def mix_wav_files(input_paths: Sequence[Path], output_path: Path) -> None:
    """Mixes mono 16-bit PCM WAV files without loading the full meeting into memory."""

    if not input_paths:
        raise RecordingError("ミックスする音声トラックがありません。")

    readers = [wave.open(str(path), "rb") for path in input_paths]
    try:
        first = readers[0]
        expected = (first.getnchannels(), first.getsampwidth(), first.getframerate())
        if expected[0] != 1 or expected[1] != 2:
            raise RecordingError("録音トラックの形式が対応外です。")
        for reader in readers[1:]:
            current = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
            if current != expected:
                raise RecordingError("録音トラックの音声形式が一致しません。")

        ensure_private_directory(output_path.parent)
        with open_private_binary_writer(output_path, exclusive=True) as raw_file:
            with wave.open(raw_file, "wb") as writer:
                writer.setnchannels(expected[0])
                writer.setsampwidth(expected[1])
                writer.setframerate(expected[2])

                while True:
                    chunks = [reader.readframes(MIX_CHUNK_FRAMES) for reader in readers]
                    if not any(chunks):
                        break

                    sample_arrays = [
                        np.frombuffer(chunk, dtype="<i2").astype(np.float32)
                        for chunk in chunks
                        if chunk
                    ]
                    frame_count = max(len(samples) for samples in sample_arrays)
                    mixed = np.zeros(frame_count, dtype=np.float32)
                    for samples in sample_arrays:
                        mixed[: len(samples)] += samples

                    # A soft per-track gain leaves headroom while keeping a lone
                    # voice track near its original level.
                    gain = 1.0 if len(sample_arrays) == 1 else 0.7
                    mixed = np.clip(mixed * gain, -32768, 32767).astype("<i2")
                    writer.writeframes(mixed.tobytes())
    finally:
        for reader in readers:
            reader.close()
