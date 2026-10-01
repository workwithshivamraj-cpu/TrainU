"""Embeddings provider abstraction.

Two providers are implemented:

- ``mock`` (default, no network/API key required): a deterministic hashed
  bag-of-words embedding. It is not a "real" semantic embedding model, but
  because it is a normalized feature-hashed term vector, cosine similarity
  between it and a query embedding rewards literal vocabulary overlap between
  the question and the transcript/document text — which is exactly the
  behavior the demo needs to return sensible, grounded citations without any
  paid API.
- ``openai`` / ``ollama``: real HTTP adapters using OpenAI-compatible
  ``/embeddings`` endpoints, selected via ``EMBEDDINGS_PROVIDER``.
"""
from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections import Counter

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common English function words carry no topical signal and, left in, cause
# unrelated questions ("What is the capital of France?") to spuriously
# overlap with indexed content through words like "the"/"is"/"what". Mock
# mode is a lexical-overlap approximation of semantic search, so stripping
# stopwords is what keeps it from returning false-positive citations.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "of", "to", "in",
    "on", "at", "by", "for", "with", "about", "as", "is", "are", "was", "were",
    "be", "been", "being", "it", "its", "this", "that", "these", "those",
    "what", "who", "whom", "which", "when", "where", "why", "how", "do", "does",
    "did", "can", "could", "should", "would", "will", "shall", "may", "might",
    "i", "you", "he", "she", "we", "they", "them", "his", "her", "our", "your",
    "their", "my", "me", "us", "not", "no", "yes", "up", "down", "out", "into",
    "over", "under", "again", "further", "just", "than", "too", "very", "s",
    "t", "there", "here", "all", "any", "each", "some", "such", "own", "same",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class EmbeddingsProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class MockEmbeddingsProvider(EmbeddingsProvider):
    def __init__(self, dim: int = settings.EMBEDDING_DIM):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        vec = [0.0] * self.dim
        if not tokens:
            return vec
        counts = Counter(tokens)
        for token, count in counts.items():
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            h = int(digest, 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class OpenAICompatibleEmbeddingsProvider(EmbeddingsProvider):
    """Works against any OpenAI-compatible or Ollama-compatible
    ``/embeddings`` endpoint. Requires network access and, for OpenAI, an API
    key — not exercised in the offline demo/test environment."""

    def __init__(self) -> None:
        self.base_url = settings.EMBEDDINGS_BASE_URL.rstrip("/")
        self.api_key = settings.EMBEDDINGS_API_KEY
        self.model = settings.EMBEDDINGS_MODEL

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = httpx.post(
                f"{self.base_url}/embeddings",
                json={"model": self.model, "input": texts, **(
                    {"dimensions": settings.EMBEDDING_DIM}
                    if settings.EMBEDDINGS_PROVIDER == "openai" and self.model.startswith("text-embedding-3") else {}
                )},
                headers=headers,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            vectors = [item["embedding"] for item in sorted(data["data"], key=lambda item: item.get("index", 0))]
            if len(vectors) != len(texts) or any(len(v) != settings.EMBEDDING_DIM for v in vectors):
                raise ValueError("Embedding provider returned an unexpected vector dimension or count")
            if any(not math.isfinite(float(n)) for v in vectors for n in v):
                raise ValueError("Embedding provider returned a non-finite vector")
            return vectors
        except Exception:  # noqa: BLE001
            logger.error("embeddings_provider_error", provider=settings.EMBEDDINGS_PROVIDER)
            raise


def get_embeddings_provider() -> EmbeddingsProvider:
    if settings.EMBEDDINGS_PROVIDER == "mock":
        return MockEmbeddingsProvider()
    return OpenAICompatibleEmbeddingsProvider()
