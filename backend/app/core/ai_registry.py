"""Validated, operator-owned registry for model/provider selection.

The registry contains provider metadata and secret *references*, never secret
values. It performs no endpoint discovery or network requests. Tenant policy
and runtime adapters are layered on later release tasks.
"""
from __future__ import annotations

import json
import ipaddress
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

Capability = Literal["chat", "transcription", "embeddings"]
Deployment = Literal["local", "hosted"]
SelectionMode = Literal["manual", "auto"]
Adapter = Literal[
    "mock",
    "ollama_chat_completions",
    "openai_chat_completions",
    "openai_responses",
    "compatible_chat_completions",
    "openai_embeddings",
    "ollama_embeddings",
    "compatible_embeddings",
    "whisper_api",
    "faster_whisper",
    "sentence_transformers",
]

_ID = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
_SECRET_REF = re.compile(
    r"^(?:TRAINU_AI_SECRET_[A-Z0-9_]{1,80}|(?:STT|LLM|EMBEDDINGS)_API_KEY)$"
)
_LOCAL_ENDPOINT_HOSTS = {"localhost", "host.docker.internal", "ollama"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Endpoint(StrictModel):
    id: str
    base_url: str = Field(min_length=8, max_length=500)
    deployment: Deployment
    secret_ref: str | None = None

    @model_validator(mode="after")
    def validate_endpoint(self) -> "Endpoint":
        if not _ID.fullmatch(self.id):
            raise ValueError("Endpoint ID must be a lowercase stable identifier")
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme not in ({"https"} if self.deployment == "hosted" else {"http", "https"})
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Endpoint URL must use an allowed scheme and contain no credentials/query")
        if self.deployment == "local":
            hostname = parsed.hostname.lower().rstrip(".")
            try:
                loopback = ipaddress.ip_address(hostname).is_loopback
            except ValueError:
                loopback = hostname in _LOCAL_ENDPOINT_HOSTS
            if not loopback:
                raise ValueError("Local model endpoints must use a loopback or approved local service host")
        if self.secret_ref is not None and not _SECRET_REF.fullmatch(self.secret_ref):
            raise ValueError("Credentials must use an approved TRAINU_AI_SECRET_* reference")
        return self


class Profile(StrictModel):
    id: str
    capability: Capability
    adapter: Adapter
    deployment: Deployment
    enabled: bool = True
    model_id: str = Field(min_length=1, max_length=180)
    revision: str | None = Field(default=None, max_length=200)
    endpoint_id: str | None = None
    secret_ref: str | None = None
    capabilities: frozenset[str] = frozenset()
    supported_parameters: frozenset[str] = frozenset()
    max_input_tokens: int | None = Field(default=None, ge=1, le=2_000_000)
    max_output_tokens: int | None = Field(default=None, ge=1, le=128_000)
    connect_timeout_seconds: int = Field(default=5, ge=1, le=120)
    request_timeout_seconds: int = Field(default=120, ge=1, le=600)
    qualification_ref: str | None = Field(default=None, max_length=240)
    dimension: int | None = Field(default=None, ge=1, le=65536)
    normalized: bool | None = None
    query_transform: str | None = None
    document_transform: str | None = None

    @model_validator(mode="after")
    def validate_profile(self) -> "Profile":
        if not _ID.fullmatch(self.id):
            raise ValueError("Profile ID must be a lowercase stable identifier")
        if self.secret_ref is not None and not _SECRET_REF.fullmatch(self.secret_ref):
            raise ValueError("Credentials must use an approved TRAINU_AI_SECRET_* reference")
        if self.capability == "embeddings":
            if self.dimension != 384 or self.normalized is not True:
                raise ValueError("This release supports normalized 384-dimensional embeddings only")
            if not self.query_transform or not self.document_transform:
                raise ValueError("Embedding profiles must identify query and document transforms")
        elif any(
            value is not None
            for value in (self.dimension, self.normalized, self.query_transform, self.document_transform)
        ):
            raise ValueError("Embedding settings are only valid on embedding profiles")
        if self.capability == "transcription" and "timestamps" not in self.capabilities:
            raise ValueError("Transcription profiles must declare timestamp support")
        adapters_by_capability = {
            "chat": {"mock", "ollama_chat_completions", "openai_chat_completions",
                     "openai_responses", "compatible_chat_completions"},
            "transcription": {"mock", "whisper_api", "faster_whisper"},
            "embeddings": {"mock", "openai_embeddings", "ollama_embeddings",
                           "compatible_embeddings", "sentence_transformers"},
        }
        if self.adapter not in adapters_by_capability[self.capability]:
            raise ValueError("Provider adapter does not support the declared capability")
        local_adapters = {"mock", "ollama_chat_completions", "ollama_embeddings", "faster_whisper", "sentence_transformers"}
        if self.adapter in local_adapters and self.deployment != "local":
            raise ValueError("Local adapters must be marked local")
        return self


class Selection(StrictModel):
    mode: SelectionMode
    profile_id: str | None = None
    priority: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_selection(self) -> "Selection":
        if self.mode == "manual" and (not self.profile_id or self.priority):
            raise ValueError("Manual selection requires one profile and no priority list")
        if self.mode == "auto" and (self.profile_id is not None or not self.priority):
            raise ValueError("Automatic selection requires an ordered priority list only")
        if len(set(self.priority)) != len(self.priority):
            raise ValueError("Automatic selection priority cannot contain duplicates")
        return self


class ProviderRegistry(StrictModel):
    schema_version: Literal[1]
    endpoints: tuple[Endpoint, ...] = ()
    profiles: tuple[Profile, ...] = Field(min_length=1, max_length=100)
    selection: dict[Capability, Selection]
    allow_hosted: bool = False

    @model_validator(mode="after")
    def validate_references(self) -> "ProviderRegistry":
        endpoint_ids = [endpoint.id for endpoint in self.endpoints]
        profile_ids = [profile.id for profile in self.profiles]
        if len(set(endpoint_ids)) != len(endpoint_ids) or len(set(profile_ids)) != len(profile_ids):
            raise ValueError("Endpoint and profile IDs must be unique")
        endpoints = {endpoint.id: endpoint for endpoint in self.endpoints}
        profiles = {profile.id: profile for profile in self.profiles}
        for profile in self.profiles:
            endpoint = endpoints.get(profile.endpoint_id) if profile.endpoint_id else None
            if profile.endpoint_id:
                if endpoint is None or endpoint.deployment != profile.deployment:
                    raise ValueError("Profile references an unknown or mismatched endpoint")
            elif profile.adapter in {
                "ollama_chat_completions", "openai_chat_completions", "openai_responses",
                "compatible_chat_completions", "openai_embeddings", "ollama_embeddings",
                "compatible_embeddings", "whisper_api",
            }:
                raise ValueError("HTTP provider profiles must reference a registered endpoint")
            if profile.deployment == "hosted" and profile.adapter in {
                "openai_chat_completions", "openai_responses", "openai_embeddings", "whisper_api"
            } and not (profile.secret_ref or (endpoint and endpoint.secret_ref)):
                raise ValueError("Hosted provider profiles require an approved credential reference")
        if set(self.selection) != {"chat", "transcription", "embeddings"}:
            raise ValueError("Selection policy must define chat, transcription and embeddings")
        for capability, rule in self.selection.items():
            selected = (rule.profile_id,) if rule.mode == "manual" else rule.priority
            for profile_id in selected:
                profile = profiles.get(profile_id)
                if profile is None or profile.capability != capability:
                    raise ValueError("Selection policy references a missing or wrong-capability profile")
                if rule.mode == "manual" and not profile.enabled:
                    raise ValueError("Manual selection cannot target a disabled profile")
                if profile.deployment == "hosted" and not self.allow_hosted:
                    raise ValueError("Hosted profiles require explicit operator enablement")
        return self

    def resolve(self, capability: Capability, *, available_profile_ids: set[str] | None = None) -> Profile:
        """Resolve a manual profile or first available auto candidate deterministically."""
        rule = self.selection[capability]
        candidates = (rule.profile_id,) if rule.mode == "manual" else rule.priority
        profiles = {profile.id: profile for profile in self.profiles}
        if rule.mode == "manual":
            profile = profiles[rule.profile_id]  # validated by the model
            if available_profile_ids is not None and profile.id not in available_profile_ids:
                raise ProviderUnavailable("The selected model profile is unavailable")
            return profile
        for profile_id in candidates:
            profile = profiles[profile_id]
            if profile.enabled and (available_profile_ids is None or profile_id in available_profile_ids):
                if profile.deployment != "hosted" or self.allow_hosted:
                    return profile
        raise ProviderUnavailable("No permitted model profile is currently available")


class ProviderUnavailable(RuntimeError):
    """No configured, permitted model endpoint can handle a capability."""


def load_registry(path: str | Path) -> ProviderRegistry:
    """Read and validate a small operator registry without logging contents."""
    registry_path = Path(path)
    try:
        if registry_path.stat().st_size > 256 * 1024:
            raise ValueError
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
        return ProviderRegistry.model_validate(raw)
    except Exception:
        # Pydantic/JSON exceptions may echo endpoint strings. Do not leak them
        # into logs or diagnostics, where URLs could contain operator data.
        raise ValueError("AI provider registry is unreadable or invalid; check its schema and IDs") from None


def resolve_secret(reference: str | None, *, environ: dict[str, str] | None = None) -> str | None:
    """Resolve only an allowlisted environment variable reference."""
    if reference is None:
        return None
    if not _SECRET_REF.fullmatch(reference):
        raise ValueError("Invalid AI provider secret reference")
    value = (os.environ if environ is None else environ).get(reference)
    if not value:
        raise ProviderUnavailable("A credential for the selected model profile is not configured")
    return value


def legacy_registry(settings: object, *, allow_hosted: bool = False) -> ProviderRegistry:
    """Translate existing environment settings into one explicit registry.

    This keeps deployments on their current provider selection while allowing
    the new registry to become an opt-in configuration source. No secret value
    is copied into the registry; only the existing environment variable name
    is retained as a secret reference.
    """
    endpoints: dict[tuple[str, str], Endpoint] = {}
    profiles: list[Profile] = []
    selected: dict[str, str] = {}

    def endpoint(url: str, deployment: Deployment, secret_ref: str | None) -> str:
        key = (url.rstrip("/"), deployment)
        if key not in endpoints:
            endpoint_id = f"legacy-endpoint-{len(endpoints) + 1}"
            endpoints[key] = Endpoint(
                id=endpoint_id, base_url=url.rstrip("/"), deployment=deployment,
                secret_ref=secret_ref,
            )
        elif secret_ref and not endpoints[key].secret_ref:
            # A shared base URL with credentials is still safe; keep the first
            # reference only and each profile retains its own reference below.
            pass
        return endpoints[key].id

    def add(capability: Capability, provider: str, base_url: str, model: str,
            api_key: str, secret_name: str, revision: str | None = None) -> None:
        deployment: Deployment = "hosted" if provider in {"openai", "whisper_api"} else "local"
        if deployment == "hosted" and not api_key:
            raise ValueError("A hosted legacy provider requires its API key setting")
        secret_ref = secret_name if api_key else None
        adapter_by_provider = {
            "mock": "mock",
            "ollama": "ollama_chat_completions" if capability == "chat" else "ollama_embeddings",
            "openai": "openai_chat_completions" if capability == "chat" else "openai_embeddings",
            "whisper_api": "whisper_api",
        }
        adapter = adapter_by_provider[provider]
        endpoint_id = None
        if provider != "mock":
            endpoint_id = endpoint(base_url, deployment, secret_ref)
        profile_id = f"legacy-{capability}"
        values: dict[str, object] = {
            "id": profile_id, "capability": capability, "adapter": adapter,
            "deployment": deployment, "model_id": model, "revision": revision,
            "endpoint_id": endpoint_id, "secret_ref": secret_ref,
        }
        if capability == "transcription":
            values["capabilities"] = frozenset({"timestamps", "language-detection"})
        if capability == "embeddings":
            values.update(
                dimension=int(getattr(settings, "EMBEDDING_DIM", 384)), normalized=True,
                query_transform="query-prefix-v1", document_transform="passage-prefix-v1",
            )
        profiles.append(Profile.model_validate(values))
        selected[capability] = profile_id

    add("chat", str(getattr(settings, "LLM_PROVIDER")),
        str(getattr(settings, "LLM_BASE_URL")), str(getattr(settings, "LLM_MODEL")),
        str(getattr(settings, "LLM_API_KEY", "")), "LLM_API_KEY",
        str(getattr(settings, "LLM_MODEL_DIGEST", "")) or None)
    add("transcription", str(getattr(settings, "STT_PROVIDER")),
        str(getattr(settings, "STT_API_BASE_URL", "")) or "http://localhost:8000",
        str(getattr(settings, "STT_MODEL", "whisper-1")),
        str(getattr(settings, "STT_API_KEY", "")), "STT_API_KEY")
    add("embeddings", str(getattr(settings, "EMBEDDINGS_PROVIDER")),
        str(getattr(settings, "EMBEDDINGS_BASE_URL")),
        str(getattr(settings, "EMBEDDINGS_MODEL")),
        str(getattr(settings, "EMBEDDINGS_API_KEY", "")), "EMBEDDINGS_API_KEY",
        str(getattr(settings, "EMBEDDING_MODEL_REVISION", "")) or None)
    return ProviderRegistry.model_validate({
        "schema_version": 1,
        "endpoints": tuple(endpoints.values()),
        "profiles": tuple(profiles),
        "selection": {
            capability: {"mode": "manual", "profile_id": profile_id}
            for capability, profile_id in selected.items()
        },
        "allow_hosted": allow_hosted,
    })


def configured_registry(settings: object) -> ProviderRegistry:
    """Load an explicit registry, or safely translate current legacy settings."""
    path = str(getattr(settings, "AI_PROVIDER_CONFIG_PATH", "") or "").strip()
    if path:
        registry = load_registry(path)
        if registry.allow_hosted and not bool(getattr(settings, "AI_ALLOW_HOSTED", False)):
            raise ValueError("Hosted model profiles require AI_ALLOW_HOSTED=true")
        return registry
    return legacy_registry(settings, allow_hosted=bool(getattr(settings, "AI_ALLOW_HOSTED", False)))
