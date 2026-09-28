"""Turn raw transcript segments or document text into meaningful, retrievable
chunks with precise timestamps (video) or section titles (documents).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.stt import TranscriptSegment

MIN_CHUNK_SECONDS = 30.0
MAX_CHUNK_SECONDS = 90.0


@dataclass
class Chunk:
    title: str
    topic: str
    text: str
    start_seconds: float
    end_seconds: float


def chunk_transcript(segments: list[TranscriptSegment], source_title: str) -> list[Chunk]:
    """Greedily group consecutive transcript segments into 30-90s semantic
    chunks, breaking on sentence boundaries so each chunk reads cleanly and
    lines up with a playable, citation-worthy video clip.
    """
    if not segments:
        return []

    chunks: list[Chunk] = []
    buffer: list[TranscriptSegment] = []

    def flush() -> None:
        if not buffer:
            return
        text = " ".join(s.text for s in buffer)
        topic = _derive_topic(text)
        chunks.append(
            Chunk(
                title=f"{source_title} — {topic}",
                topic=topic,
                text=text,
                start_seconds=buffer[0].start_seconds,
                end_seconds=buffer[-1].end_seconds,
            )
        )

    for seg in segments:
        buffer.append(seg)
        span = buffer[-1].end_seconds - buffer[0].start_seconds
        if span >= MIN_CHUNK_SECONDS and (span >= MAX_CHUNK_SECONDS or seg.text.strip().endswith((".", "!", "?"))):
            flush()
            buffer = []
    flush()
    return chunks


def _derive_topic(text: str) -> str:
    cleaned = re.sub(r"^#+\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"[#*_`]", "", cleaned).strip()
    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned)[0] if cleaned else "Untitled section"
    words = first_sentence.split()
    return " ".join(words[:8]) + ("…" if len(words) > 8 else "")


def chunk_document(text: str, source_title: str) -> list[Chunk]:
    """Split plain document text into paragraph-based chunks. Documents don't
    have timestamps, so start/end seconds are 0 and the UI shows them as a
    document reference rather than a video clip.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[Chunk] = []
    buffer = ""
    for para in paragraphs:
        candidate = (buffer + "\n\n" + para).strip() if buffer else para
        if len(candidate) > 1200 and buffer:
            chunks.append(Chunk(title=f"{source_title} — {_derive_topic(buffer)}", topic=_derive_topic(buffer), text=buffer, start_seconds=0, end_seconds=0))
            buffer = para
        else:
            buffer = candidate
    if buffer:
        chunks.append(Chunk(title=f"{source_title} — {_derive_topic(buffer)}", topic=_derive_topic(buffer), text=buffer, start_seconds=0, end_seconds=0))
    return chunks
