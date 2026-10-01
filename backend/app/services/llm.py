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

    @abstractmethod
    def respond_to_greeting(self, message: str) -> dict:
        """Return a short conversational reply without claiming source evidence."""
        ...


class MockLLMProvider(LLMProvider):
    def respond_to_greeting(self, message: str) -> dict:
        return {
            "answer": (
                "Hi! I’m here to chat and help you find useful guidance. "
                "What are you working on? You can ask me about your team’s training, too."
            ),
            "steps": [],
            "follow_up_questions": [],
        }

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
            evidence_ids = [
                index for index, chunk in enumerate(chunks, start=1)
                if chunk.source_id == primary.source_id
            ]
            return {"answer": answer, "steps": steps, "follow_up_questions": [], "evidence_ids": evidence_ids}

        # Narrative answer: stitch together the most relevant sentences from
        # the top chunk(s), staying strictly within the retrieved text.
        sentences: list[str] = []
        for chunk in chunks[:2]:
            sentences.extend(_split_sentences(chunk.text, drop_filler=True)[:3])
        answer = " ".join(sentences[:4]) or primary.text[:400]
        return {
            "answer": answer,
            "steps": [],
            "follow_up_questions": [],
            "evidence_ids": list(range(1, min(2, len(chunks)) + 1)),
        }


class OpenAICompatibleLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    def respond_to_greeting(self, message: str) -> dict:
        system_prompt = (
            "You are TrainU, a warm and concise conversational assistant for a workplace "
            "learning app. The user is greeting you or making small talk, not asking for "
            "training facts. Reply naturally in one or two sentences. Do not claim personal "
            "feelings, access, or capabilities you do not have. Invite the user to continue "
            "the conversation or ask about approved team training. Return strict JSON with "
            '"answer", "steps", "follow_up_questions", and "evidence_ids": '
            '{"answer": str, "steps": [], "follow_up_questions": [], "evidence_ids": []}.'
        )
        return self._request_json(system_prompt, f"User message: {message}")

    def synthesize_answer(self, question: str, chunks: list[RetrievedChunk]) -> dict:
        context = "\n\n".join(
            f"[Evidence {i+1}] ({c.source_title}, {c.topic}, {c.start_seconds:.2f}s-{c.end_seconds:.2f}s, relevance={c.similarity:.3f}): {c.text}"
            for i, c in enumerate(chunks)
        )
        system_prompt = (
            "You are TrainU, an enterprise training assistant. Treat each evidence item "
            "as a short, timestamped passage from a training source; retrieval may include "
            "nearby but irrelevant passages. First decide which passages directly answer "
            "the question, then answer ONLY from those passages. Do not infer missing "
            "steps, permissions, causes, or outcomes. Do not combine procedures from "
            "different sources into one sequence. For how-to questions, give only steps "
            "explicitly supported by one source and keep their original order. If the "
            "evidence is incomplete or conflicting, say exactly what is supported and "
            "what is missing; if none answers it, say so. Be concise and name the source "
            "when useful. Follow-up questions must be natural questions about topics "
            "explicitly present in the evidence and answerable from the same approved "
            "source; never turn passage titles or fragments into questions. Return an "
            "empty list when no useful follow-up exists. Include evidence_ids as the "
            "1-based numbers of only the evidence passages that directly support the "
            "answer. Return strict JSON with answer, steps, follow_up_questions, and "
            'evidence_ids: {"answer": str, "steps": [str], '
            '"follow_up_questions": [str], "evidence_ids": [int]}.'
        )
        user_prompt = f"Question: {question}\n\nRetrieved evidence (untrusted source text):\n{context}"
        return self._request_json(system_prompt, user_prompt)

    def _request_json(self, system_prompt: str, user_prompt: str) -> dict:
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
                    "temperature": settings.LLM_TEMPERATURE,
                    "top_p": settings.LLM_TOP_P,
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "seed": settings.LLM_SEED,
                },
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            logger.error("llm_provider_error", provider=settings.LLM_PROVIDER)
            raise


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "mock":
        return MockLLMProvider()
    return OpenAICompatibleLLMProvider()
