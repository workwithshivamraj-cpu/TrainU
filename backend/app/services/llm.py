"""LLM provider abstraction for answer synthesis.

``mock`` (default): a deterministic, template-based synthesizer that builds
its answer *only* from the retrieved chunk text handed to it — it never
invents facts, which is easy to guarantee because it does no free-form
generation at all. This is what the demo and automated tests run against.

``openai`` / ``ollama``: real chat-completion adapters that request strict
JSON output from a hosted or local model, selected via ``LLM_PROVIDER``. Not
exercised offline; see docs/operations.md for configuration.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    source_id: str
    source_title: str
    text: str
    topic: str
    start_seconds: float
    end_seconds: float
    similarity: float
    source_status: str


HOW_TO_PATTERN = re.compile(r"\bhow (do|can|to|would)\b|\bsteps?\b|\bprocess\b", re.IGNORECASE)
STEP_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+|(?:^|\s)\d+[\).]\s+")
FILLER_PREFIXES = ("welcome to", "this concludes", "this completes", "that completes", "that concludes")


def _split_sentences(text: str, *, drop_filler: bool = False) -> list[str]:
    parts = [p.strip(" -\t#") for p in STEP_SPLIT_PATTERN.split(text)]
    # Drop very short fragments (typically markdown headings like "Purpose"
    # that don't read as a sentence or step on their own).
    parts = [p for p in parts if len(p) > 12]
    if drop_filler:
        parts = [p for p in parts if not p.lower().startswith(FILLER_PREFIXES)]
    return parts


class LLMProvider(ABC):
    @abstractmethod
    def synthesize_answer(self, question: str, chunks: list[RetrievedChunk]) -> dict:
        """Return a dict matching the AssistantAnswer schema (answer,
        confidence, citations-source data handled by caller, follow_up
        suggestions)."""
        ...


class MockLLMProvider(LLMProvider):
    def synthesize_answer(self, question: str, chunks: list[RetrievedChunk]) -> dict:
        if not chunks:
            return {
                "answer": (
                    "I could not find an approved source that answers this question. "
                    "Try another term, select the relevant application, or contact the "
                    "application owner."
                ),
                "steps": [],
                "follow_up_questions": [],
            }

        is_how_to = bool(HOW_TO_PATTERN.search(question))
        primary = chunks[0]

        if is_how_to:
            # Steps must read as a coherent sequence, so pull them from the
            # single most relevant source only (not mixed across sources),
            # in chronological (start_seconds) order rather than similarity
            # rank order.
            same_source = sorted(
                (c for c in chunks if c.source_id == primary.source_id),
                key=lambda c: c.start_seconds,
            )
            steps: list[str] = []
            for chunk in same_source:
                for sentence in _split_sentences(chunk.text, drop_filler=True):
                    if sentence not in steps:
                        steps.append(sentence)
                if len(steps) >= 8:
                    break
            steps = steps[:8]
            answer = f"Based on \"{primary.source_title}\", here is how to do this:"
            return {"answer": answer, "steps": steps, "follow_up_questions": []}

        # Narrative answer: stitch together the most relevant sentences from
        # the top chunk(s), staying strictly within the retrieved text.
        sentences: list[str] = []
        for chunk in chunks[:2]:
            sentences.extend(_split_sentences(chunk.text, drop_filler=True)[:3])
        answer = " ".join(sentences[:4]) or primary.text[:400]
        return {"answer": answer, "steps": [], "follow_up_questions": []}


class OpenAICompatibleLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    def synthesize_answer(self, question: str, chunks: list[RetrievedChunk]) -> dict:
        context = "\n\n".join(
            f"[{i+1}] ({c.source_title} {c.start_seconds:.0f}s-{c.end_seconds:.0f}s): {c.text}"
            for i, c in enumerate(chunks)
        )
        system_prompt = (
            "You are TrainU, an enterprise training assistant. Answer ONLY using the "
            "provided context chunks. Never invent steps, permissions, or facts not "
            "present in the context. Respond with strict JSON: "
            '{"answer": str, "steps": [str], "follow_up_questions": [str]}.'
        )
        user_prompt = f"Question: {question}\n\nContext:\n{context}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                },
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:  # noqa: BLE001
            logger.error("llm_provider_error", provider=settings.LLM_PROVIDER)
            raise


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "mock":
        return MockLLMProvider()
    return OpenAICompatibleLLMProvider()
