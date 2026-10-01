#!/usr/bin/env python3
"""Validate provider configuration without making network requests or printing secrets."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = next(
    (candidate for candidate in (ROOT / "backend", ROOT, Path("/app"))
     if (candidate / "app/core").is_dir()),
    ROOT,
)
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.ai_registry import configured_registry, load_registry  # noqa: E402
from app.core.config import Settings  # noqa: E402


def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: scripts/validate_ai_provider_config.py [registry.json]", file=sys.stderr)
        return 2
    try:
        settings = Settings()
        if len(sys.argv) == 2:
            registry = load_registry(sys.argv[1])
            if registry.allow_hosted and not settings.AI_ALLOW_HOSTED:
                raise ValueError("Hosted model profiles require AI_ALLOW_HOSTED=true")
        else:
            registry = configured_registry(settings)
    except Exception:
        print(
            "AI provider configuration invalid; check schema, IDs and operator consent.",
            file=sys.stderr,
        )
        return 1
    print(
        "AI provider configuration valid; "
        f"profiles={len(registry.profiles)} hosted_enabled={registry.allow_hosted}"
    )
    for capability in ("chat", "transcription", "embeddings"):
        profile = registry.resolve(capability)  # type: ignore[arg-type]
        print(f"  {capability}: {profile.id} ({profile.deployment}, {profile.adapter})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
