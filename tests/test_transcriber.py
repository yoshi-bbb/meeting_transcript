import pytest

from meeting_mojiokoshi.audio import AudioDevice, preferred_device_index, preferred_microphone_index
from meeting_mojiokoshi.transcriber import (
    WhisperTranscriber,
    _is_retryable_download_error,
    format_timestamp,
    model_is_available,
    prepare_model,
)


def test_format_timestamp() -> None:
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(62.9) == "00:01:02"
    assert format_timestamp(3661) == "01:01:01"
    assert format_timestamp(-5) == "00:00:00"


def test_preferred_device_index_uses_loopback() -> None:
    devices = [
        AudioDevice(
            index=0,
            backend_id="mic",
            name="Microphone",
            label="0: Microphone",
            is_loopback_like=False,
        ),
        AudioDevice(
            index=1,
            backend_id="speaker",
            name="Speakers",
            label="1: Speakers",
            is_loopback_like=True,
        ),
    ]

    assert preferred_device_index(devices) == 1
    assert preferred_microphone_index(devices) == 0


def test_model_download_retry_classifier() -> None:
    assert _is_retryable_download_error(RuntimeError("429 Too Many Requests"))
    assert not _is_retryable_download_error(ValueError("unknown model"))


def test_whisper_transcriber_rejects_untrusted_model_size() -> None:
    with pytest.raises(ValueError, match="Unsupported model size"):
        WhisperTranscriber(model_size="large-v3")


def test_model_is_available_uses_trusted_download(tmp_path, monkeypatch) -> None:
    calls: list[bool] = []

    def fake_download(trusted, *, cache_dir, local_files_only=False):
        calls.append(local_files_only)
        return cache_dir / trusted.size

    monkeypatch.setattr("meeting_mojiokoshi.transcriber.download_trusted_model", fake_download)

    assert model_is_available("tiny", model_cache_dir=tmp_path) is True
    assert calls == [True]


def test_prepare_model_uses_trusted_download(tmp_path, monkeypatch) -> None:
    trusted_path = tmp_path / "tiny-model"

    def fake_download(trusted, *, cache_dir, local_files_only=False):
        assert local_files_only is False
        return trusted_path

    monkeypatch.setattr("meeting_mojiokoshi.transcriber.download_trusted_model", fake_download)

    assert prepare_model("tiny", model_cache_dir=tmp_path) == trusted_path


def test_transcribe_prepares_model_when_not_cached(tmp_path, monkeypatch) -> None:
    prepared_path = tmp_path / "prepared-model"
    calls: list[str] = []

    def fake_prepare(model_size, model_cache_dir=None, progress=None, retries=3):
        calls.append(model_size)
        return prepared_path

    class FakeModel:
        def __init__(self, model_path, **_kwargs):
            assert model_path == str(prepared_path)

        def transcribe(self, _audio_path, **_kwargs):
            info = type("Info", (), {"language": "ja", "duration": 0.0})()
            return iter(()), info

    monkeypatch.setattr("meeting_mojiokoshi.transcriber.prepare_model", fake_prepare)
    monkeypatch.setattr("faster_whisper.WhisperModel", FakeModel)

    audio_path = tmp_path / "meeting.wav"
    audio_path.write_bytes(b"not-read-by-fake")
    transcript_path = tmp_path / "meeting.txt"

    WhisperTranscriber(model_size="tiny", model_cache_dir=tmp_path / "models").transcribe(
        audio_path,
        transcript_path,
    )

    assert calls == ["tiny"]
    assert transcript_path.exists()
