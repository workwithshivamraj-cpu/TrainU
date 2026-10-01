"""Speech-to-text provider abstraction.

``mock`` (default): produces a deterministic, plausible timestamped
transcript without needing any audio decoding or model weights, so the whole
pipeline runs in a demo/CI environment with no external dependencies. If the
source has seed-provided transcript text (see ``worker/seed_transcripts.py``)
that is used verbatim; otherwise a short generic transcript is generated.

``whisper_api``: a real adapter for any Whisper-API-compatible
``/audio/transcriptions`` endpoint (OpenAI or a self-hosted
faster-whisper-server). Not exercised offline.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str


def apply_time_offset(
    segments: list[TranscriptSegment],
    offset_seconds: float,
    *,
    max_duration_seconds: float | None = None,
) -> list[TranscriptSegment]:
    """Map request-local timestamps to source time and clamp to media bounds."""
    shifted = []
    for segment in segments:
        start = max(0.0, segment.start_seconds + offset_seconds)
        end = segment.end_seconds + offset_seconds
        if max_duration_seconds is not None:
            end = min(end, max_duration_seconds)
        if end > start and segment.text.strip():
            shifted.append(TranscriptSegment(start, end, segment.text.strip()))
    return shifted


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, *, seed_text: str | None = None) -> list[TranscriptSegment]:
        ...


class MockSTTProvider(STTProvider):
    """Deterministic mock transcription.

    If ``seed_text`` is supplied (used by the seed script / demo uploads) it
    is split into evenly-timed segments so timestamps are stable and
    reproducible. Otherwise a short placeholder transcript is produced so the
    pipeline still completes for arbitrary uploaded videos in demo mode.
    """

    SEGMENT_SECONDS = 12.0

    def transcribe(self, audio_path: str, *, seed_text: str | None = None) -> list[TranscriptSegment]:
        text = seed_text or (
            "This is a demo transcript generated in mock speech-to-text mode. "
            "Configure STT_PROVIDER=whisper_api with STT_API_BASE_URL and STT_API_KEY "
            "to transcribe real audio."
        )
        sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
        segments: list[TranscriptSegment] = []
        t = 0.0
        for sentence in sentences:
            if not sentence.endswith((".", "!", "?")):
                sentence += "."
            duration = max(4.0, min(20.0, len(sentence.split()) * 0.55))
            segments.append(TranscriptSegment(start_seconds=t, end_seconds=t + duration, text=sentence))
            t += duration
        return segments


class WhisperAPISTTProvider(STTProvider):
    def __init__(self) -> None:
        self.base_url = settings.STT_API_BASE_URL.rstrip("/")
        self.api_key = settings.STT_API_KEY
        self.model = settings.STT_MODEL

    def transcribe(self, audio_path: str, *, seed_text: str | None = None) -> list[TranscriptSegment]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            with open(audio_path, "rb") as f:
                resp = httpx.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    data={"model": self.model, "response_format": "verbose_json"},
                    files={"file": f},
                    timeout=300.0,
                )
            resp.raise_for_status()
            data = resp.json()
            return [
                TranscriptSegment(
                    start_seconds=seg["start"], end_seconds=seg["end"], text=seg["text"].strip()
                )
                for seg in data.get("segments", [])
            ]
        except Exception:
            logger.error("stt_provider_error", provider=settings.STT_PROVIDER)
            raise


def get_stt_provider() -> STTProvider:
    if settings.STT_PROVIDER == "mock":
        return MockSTTProvider()
    return WhisperAPISTTProvider()
