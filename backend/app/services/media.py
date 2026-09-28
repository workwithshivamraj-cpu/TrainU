"""FFmpeg-backed media helpers: audio extraction and duration probing."""
from __future__ import annotations

import shutil
import subprocess

from app.core.logging import get_logger

logger = get_logger(__name__)

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
FFPROBE_AVAILABLE = shutil.which("ffprobe") is not None


def extract_audio(input_path: str, output_path: str) -> bool:
    """Extract a mono 16kHz WAV track for transcription. Returns True on
    success. If ffmpeg isn't installed (unlikely in the provided Docker
    image, but possible in a bare local checkout), logs and returns False so
    the caller can fall back gracefully rather than crash the pipeline.
    """
    if not FFMPEG_AVAILABLE:
        logger.warning("ffmpeg_not_available")
        return False
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-vn", "-ac", "1", "-ar", "16000",
                output_path,
            ],
            check=True,
            capture_output=True,
            timeout=600,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.error("ffmpeg_extract_audio_failed", error=str(exc))
        return False


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
