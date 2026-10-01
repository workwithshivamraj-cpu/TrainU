"""Exit non-zero unless both pinned local models are completely cached."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from huggingface_hub import try_to_load_from_cache

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = Path(os.environ.get("TRAINU_MODEL_LOCK", ROOT / "infrastructure" / "model-lock.json"))
LOCK = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
CACHE = Path(os.environ["HF_HOME"]) if os.environ.get("HF_HOME") else None

models = {
    "embedding_model": "config.json",
    "transcription_model": "model.bin",
}
requested = sys.argv[1:] or list(models)
for key in requested:
    if key not in models:
        raise SystemExit(f"Unknown model key: {key}")
    model = LOCK[key]
    cached = try_to_load_from_cache(
        model["name"], models[key], revision=model["revision"], cache_dir=CACHE
    )
    if cached is None or not Path(cached).is_file():
        raise SystemExit(1)

print("Pinned model files are cached: " + ", ".join(requested))
