from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from meeting_mojiokoshi.audio import mix_wav_files


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int = 16_000) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.astype("<i2").tobytes())


def _read_wav(path: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        samples = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype="<i2")
    return sample_rate, samples


def test_mix_wav_files_combines_tracks_and_keeps_longest_length(tmp_path: Path) -> None:
    system_track = np.full(32_000, 1_000, dtype=np.int16)
    microphone_track = np.full(16_000, 2_000, dtype=np.int16)
    system_path = tmp_path / "system.wav"
    microphone_path = tmp_path / "microphone.wav"
    output_path = tmp_path / "meeting.wav"
    _write_wav(system_path, system_track)
    _write_wav(microphone_path, microphone_track)

    mix_wav_files([system_path, microphone_path], output_path)

    sample_rate, mixed = _read_wav(output_path)
    assert sample_rate == 16_000
    assert len(mixed) == 32_000
    assert np.all(mixed[:16_000] == 2_100)
    assert np.all(mixed[16_000:] == 1_000)


def test_mix_wav_files_clips_overflow(tmp_path: Path) -> None:
    loud = np.full(100, 30_000, dtype=np.int16)
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    output = tmp_path / "output.wav"
    _write_wav(first, loud)
    _write_wav(second, loud)

    mix_wav_files([first, second], output)

    _, mixed = _read_wav(output)
    assert mixed.max() == 32_767
