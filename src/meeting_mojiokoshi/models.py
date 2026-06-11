"""Trusted Whisper model definitions for Hugging Face downloads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrustedModel:
    size: str
    repo_id: str
    revision: str


# Reviewed Hugging Face repositories and immutable revision SHAs.
# Update deliberately after verifying the upstream repository contents.
TRUSTED_MODELS: dict[str, TrustedModel] = {
    "tiny": TrustedModel(
        size="tiny",
        repo_id="Systran/faster-whisper-tiny",
        revision="d90ca5fe260221311c53c58e660288d3deb8d356",  # pragma: allowlist secret
    ),
    "base": TrustedModel(
        size="base",
        repo_id="Systran/faster-whisper-base",
        revision="ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",  # pragma: allowlist secret
    ),
    "small": TrustedModel(
        size="small",
        repo_id="Systran/faster-whisper-small",
        revision="536b0662742c02347bc0e980a01041f333bce120",  # pragma: allowlist secret
    ),
    "medium": TrustedModel(
        size="medium",
        repo_id="Systran/faster-whisper-medium",
        revision="08e178d48790749d25932bbc082711ddcfdfbc4f",  # pragma: allowlist secret
    ),
}

ALLOWED_MODEL_SIZES = frozenset(TRUSTED_MODELS)


def resolve_trusted_model(model_size: str) -> TrustedModel:
    trusted = TRUSTED_MODELS.get(model_size)
    if trusted is None:
        allowed = ", ".join(sorted(ALLOWED_MODEL_SIZES))
        raise ValueError(
            f"Unsupported model size '{model_size}'. Allowed values: {allowed}"
        )
    return trusted


_MODEL_FILE_PATTERNS = (
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
)


def download_trusted_model(
    trusted: TrustedModel,
    *,
    cache_dir: Path,
    local_files_only: bool = False,
) -> Path:
    """Download or resolve a trusted model at a pinned Hugging Face revision."""

    import huggingface_hub

    from faster_whisper.utils import disabled_tqdm

    model_path = huggingface_hub.snapshot_download(
        trusted.repo_id,
        revision=trusted.revision,
        cache_dir=str(cache_dir),
        local_files_only=local_files_only,
        allow_patterns=list(_MODEL_FILE_PATTERNS),
        tqdm_class=disabled_tqdm,
    )
    return Path(model_path)
