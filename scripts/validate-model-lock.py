"""Fail early if local model pins/settings are incomplete or mutable."""
from __future__ import annotations

import json
import re
from pathlib import Path

lock = json.loads(
    (Path(__file__).resolve().parents[1] / "infrastructure" / "model-lock.json").read_text(
        encoding="utf-8"
    )
)
image_lock = json.loads(
    (Path(__file__).resolve().parents[1] / "infrastructure" / "image-lock.json").read_text(
        encoding="utf-8"
    )
)
for image_name, image in image_lock["images"].items():
    if not re.search(r"@sha256:[0-9a-f]{64}$", image):
        raise SystemExit(f"image {image_name} must use an immutable sha256 digest")

for section in ("embedding_model", "transcription_model"):
    model = lock[section]
    if not re.fullmatch(r"[0-9a-f]{40}", model.get("revision", "")):
        raise SystemExit(f"{section} must use an immutable 40-character model revision")
    if model.get("status", "").startswith("pending:"):
        raise SystemExit(f"{section} is not ready: {model['status']}")

answer = lock["answer_model"]
if not re.fullmatch(r"[0-9a-f]{64}", answer.get("digest", "")):
    raise SystemExit("answer_model must pin a full 64-character Ollama digest")
if not 0 <= answer.get("temperature", -1) <= 2:
    raise SystemExit("answer_model temperature is outside the accepted range")
if not 0 < answer.get("top_p", 0) <= 1:
    raise SystemExit("answer_model top_p is outside the accepted range")
if not 64 <= answer.get("max_tokens", 0) <= 8192:
    raise SystemExit("answer_model max_tokens is outside the accepted range")
if not isinstance(answer.get("seed"), int):
    raise SystemExit("answer_model seed must be an integer")

print("Immutable model and image pins and generation bounds are valid; inference/evaluation remains separate.")
