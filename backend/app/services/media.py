"""FFmpeg-backed media helpers: audio extraction and duration probing."""
from __future__ import annotations

import math
import os
import shutil
import subprocess

from app.core.logging import get_logger

logger = get_logger(__name__)

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
FFPROBE_AVAILABLE = shutil.which("ffprobe") is not None


def extract_audio_segments(
    input_path: str,
    output_dir: str,
    *,
    segment_seconds: int = 600,
) -> list[tuple[str, float]]:
    """Extract timestamped mono PCM segments from a video's first audio track.

    Ten minutes of 16 kHz mono PCM is about 19.2 MB, below common hosted STT
    request ceilings. Each tuple contains a temporary WAV path and its offset
    in the original video. Missing audio/tooling is an explicit failure.
    """
    if not FFMPEG_AVAILABLE or not FFPROBE_AVAILABLE:
        raise RuntimeError("FFmpeg and ffprobe are required to process video audio.")
    duration = probe_duration_seconds(input_path)
    if not duration or duration <= 0:
        raise RuntimeError("Video duration could not be read; verify that the file is a supported video.")

    segment_count = math.ceil(duration / segment_seconds)
    if segment_count > 1 and duration - (segment_count - 1) * segment_seconds < 1:
        segment_count -= 1  # Include a sub-second tail in the previous request.

    segments: list[tuple[str, float]] = []
    for index in range(segment_count):
        offset = index * segment_seconds
        output_path = os.path.join(output_dir, f"audio-{index:04d}.wav")
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", str(offset), "-i", input_path,
                    "-t", str(min(segment_seconds, duration - offset)),
                    "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", output_path,
                ],
                check=True,
                capture_output=True,
                timeout=1800,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            logger.error("ffmpeg_extract_audio_segment_failed", segment=index, error=str(exc))
            raise RuntimeError(
                "Audio could not be extracted from this video. Check that it contains a supported audio track."
            ) from exc
        if not os.path.exists(output_path) or os.path.getsize(output_path) <= 44:
            raise RuntimeError("The video contains no usable audio track to transcribe.")
        segments.append((output_path, float(offset)))
    return segments


def probe_duration_seconds(input_path: str) -> float | None:
    if not FFPROBE_AVAILABLE:
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", input_path,
            ],
            check=True,
            capture_output=True,
            timeout=60,
            text=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return None
