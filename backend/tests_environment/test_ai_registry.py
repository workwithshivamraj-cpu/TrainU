from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.ai_registry import (
    Endpoint,
    ProviderRegistry,
    ProviderUnavailable,
    configured_registry,
    legacy_registry,
    load_registry,
    resolve_secret,
)
from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_sample_registry_validates_and_resolves_local_profiles() -> None:
    registry = load_registry(ROOT / "infrastructure/ai-providers.example.json")
    assert registry.resolve("chat").id == "qwen-local"
    assert registry.resolve("transcription").id == "whisper-local"
    assert registry.resolve("embeddings").dimension == 384
    assert registry.allow_hosted is False


def test_legacy_mock_defaults_translate_without_activating_default_hosted_url() -> None:
    registry = legacy_registry(Settings(_env_file=None))
    assert all(profile.adapter == "mock" for profile in registry.profiles)
    assert not registry.endpoints
    assert not registry.allow_hosted


def test_legacy_hosted_provider_requires_explicit_consent() -> None:
    settings = Settings(_env_file=None, LLM_PROVIDER="openai", LLM_API_KEY="test-only")
    with pytest.raises(ValidationError, match="Hosted profiles require explicit operator enablement"):
        legacy_registry(settings)
    allowed = legacy_registry(settings, allow_hosted=True)
    assert allowed.resolve("chat").secret_ref == "LLM_API_KEY"
    no_key = Settings(_env_file=None, LLM_PROVIDER="openai", LLM_API_KEY="")
    with pytest.raises(ValueError, match="requires its API key setting"):
        legacy_registry(no_key, allow_hosted=True)


def test_hosted_provider_registry_requires_secret_reference() -> None:
    source = json.loads((ROOT / "infrastructure/ai-providers.example.json").read_text())
    source["allow_hosted"] = True
    source["endpoints"].append({
        "id": "hosted-openai", "base_url": "https://api.openai.com/v1", "deployment": "hosted"
    })
    source["profiles"].append({
        "id": "hosted-chat", "capability": "chat", "adapter": "openai_chat_completions",
        "deployment": "hosted", "model_id": "example-model", "endpoint_id": "hosted-openai"
    })
    source["selection"]["chat"] = {"mode": "manual", "profile_id": "hosted-chat"}
    with pytest.raises(ValidationError, match="approved credential reference"):
        ProviderRegistry.model_validate(source)


def test_explicit_registry_cannot_self_enable_hosted_inference(tmp_path: Path) -> None:
    source = json.loads((ROOT / "infrastructure/ai-providers.example.json").read_text())
    source["allow_hosted"] = True
    path = tmp_path / "hosted.json"
    path.write_text(json.dumps(source))
    settings = SimpleNamespace(AI_PROVIDER_CONFIG_PATH=str(path), AI_ALLOW_HOSTED=False)
    with pytest.raises(ValueError, match="AI_ALLOW_HOSTED=true"):
        configured_registry(settings)


def test_auto_selection_is_priority_ordered_and_availability_checked() -> None:
    source = json.loads((ROOT / "infrastructure/ai-providers.example.json").read_text())
    source["selection"]["chat"] = {"mode": "auto", "priority": ["qwen-local"]}
    registry = ProviderRegistry.model_validate(source)
    assert registry.resolve("chat", available_profile_ids={"qwen-local"}).id == "qwen-local"
    with pytest.raises(ProviderUnavailable):
        registry.resolve("chat", available_profile_ids=set())


def test_auto_selection_skips_disabled_profiles_and_adapter_mismatches_fail() -> None:
    source = json.loads((ROOT / "infrastructure/ai-providers.example.json").read_text())
    source["profiles"].append({
        "id": "qwen-disabled", "capability": "chat", "adapter": "ollama_chat_completions",
        "deployment": "local", "model_id": "qwen2.5:7b", "enabled": False,
        "endpoint_id": "local-ollama",
    })
    source["selection"]["chat"] = {
        "mode": "auto", "priority": ["qwen-disabled", "qwen-local"]
    }
    registry = ProviderRegistry.model_validate(source)
    assert registry.resolve("chat").id == "qwen-local"
    source["profiles"][0]["adapter"] = "faster_whisper"
    with pytest.raises(ValidationError, match="does not support the declared capability"):
        ProviderRegistry.model_validate(source)


def test_embedding_profile_rejects_dimension_or_missing_transform() -> None:
    source = json.loads((ROOT / "infrastructure/ai-providers.example.json").read_text())
    source["profiles"][2]["dimension"] = 768
    with pytest.raises(ValidationError, match="384-dimensional"):
        ProviderRegistry.model_validate(source)
    source["profiles"][2]["dimension"] = 384
    del source["profiles"][2]["query_transform"]
    with pytest.raises(ValidationError, match="query and document transforms"):
        ProviderRegistry.model_validate(source)


def test_invalid_registry_error_does_not_echo_sensitive_url(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"token":"secret-value", "endpoint":"https://private.example"}')
    with pytest.raises(ValueError) as error:
        load_registry(path)
    assert "secret-value" not in str(error.value)
    assert "private.example" not in str(error.value)


def test_secret_resolver_only_accepts_named_environment_references() -> None:
    assert resolve_secret("LLM_API_KEY", environ={"LLM_API_KEY": "sensitive"}) == "sensitive"
    with pytest.raises(ValueError, match="Invalid AI provider secret reference"):
        resolve_secret("AWS_SECRET_ACCESS_KEY", environ={"AWS_SECRET_ACCESS_KEY": "sensitive"})


def test_local_profile_cannot_point_at_a_public_host() -> None:
    with pytest.raises(ValidationError, match="approved local service host"):
        Endpoint(id="bad-local", base_url="https://models.example.test/v1", deployment="local")
