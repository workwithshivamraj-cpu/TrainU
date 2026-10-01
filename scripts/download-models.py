"""Download only the immutable model revisions recorded in model-lock.json."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from faster_whisper.utils import download_model
from huggingface_hub import snapshot_download

LOCK_FILE = Path(__file__).resolve().parents[1] / "infrastructure" / "model-lock.json"
lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
cache_root = os.environ.get("HF_HOME", str(LOCK_FILE.parents[1] / ".local-models" / "huggingface"))
Path(cache_root).mkdir(parents=True, exist_ok=True)

for key, filename in (
    ("transcription_model", "model.bin"),
    ("embedding_model", "config.json"),
):
    model = lock[key]
    revision = model.get("revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SystemExit(f"{model['name']} has no immutable model revision in {LOCK_FILE.name}")

whisper = lock["transcription_model"]
whisper_path = download_model(
    whisper["name"],
    revision=whisper["revision"],
    cache_dir=cache_root,
)
if not (Path(whisper_path) / "model.bin").is_file():
    raise SystemExit("Whisper download is incomplete: model.bin is missing")
print(f"Cached {whisper['name']} at pinned revision {whisper['revision']}.")

embedding = lock["embedding_model"]
embedding_path = Path(
    snapshot_download(
        repo_id=embedding["name"],
        revision=embedding["revision"],
        cache_dir=cache_root,
    )
)
if not (embedding_path / "config.json").is_file():
    raise SystemExit("Embedding model download is incomplete: config.json is missing")
print(f"Cached {embedding['name']} at pinned revision {embedding['revision']}.")
