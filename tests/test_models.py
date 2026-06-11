from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from meeting_mojiokoshi.models import (
    TRUSTED_MODELS,
    download_trusted_model,
    resolve_trusted_model,
)


def test_resolve_trusted_model_maps_known_sizes() -> None:
    trusted = resolve_trusted_model("tiny")
    assert trusted.repo_id == "Systran/faster-whisper-tiny"
    assert len(trusted.revision) == 40


def test_resolve_trusted_model_rejects_unknown_size() -> None:
    with pytest.raises(ValueError, match="Unsupported model size"):
        resolve_trusted_model("huge")


def test_trusted_models_cover_gui_options() -> None:
    assert set(TRUSTED_MODELS) == {"tiny", "base", "small", "medium"}


def test_download_trusted_model_uses_pinned_revision(tmp_path: Path) -> None:
    trusted = resolve_trusted_model("tiny")
    expected_path = tmp_path / "models" / "tiny"

    with patch("huggingface_hub.snapshot_download", return_value=str(expected_path)) as snapshot:
        result = download_trusted_model(trusted, cache_dir=tmp_path / "models")

    assert result == expected_path
    snapshot.assert_called_once()
    assert snapshot.call_args.args[0] == trusted.repo_id
    kwargs = snapshot.call_args.kwargs
    assert kwargs["revision"] == trusted.revision
    assert kwargs["local_files_only"] is False
