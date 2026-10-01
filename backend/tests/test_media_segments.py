from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import media
from app.services.stt import TranscriptSegment, apply_time_offset


@pytest.mark.parametrize(
    ("duration", "expected_offsets"),
    [(65, [0, 30, 60]), (60.5, [0, 30])],
)
def test_audio_extraction_splits_video_and_preserves_original_offsets(tmp_path, duration, expected_offsets):
    commands = []

    def fake_ffmpeg(command, **_kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"RIFF" + b"0" * 124)

    with (
        patch.object(media, "FFMPEG_AVAILABLE", True),
        patch.object(media, "FFPROBE_AVAILABLE", True),
        patch.object(media, "probe_duration_seconds", return_value=duration),
        patch.object(media.subprocess, "run", side_effect=fake_ffmpeg),
    ):
        audio_files = media.extract_audio_segments("video.mp4", str(tmp_path), segment_seconds=30)

    assert [offset for _path, offset in audio_files] == expected_offsets
    assert all("0:a:0" in command and "16000" in command for command in commands)
    local_segments = [TranscriptSegment(1.5, 3.5, "spoken words")]
    shifted = apply_time_offset(local_segments, audio_files[1][1], max_duration_seconds=32)
    assert [(segment.start_seconds, segment.end_seconds) for segment in shifted] == [(31.5, 32)]


def test_missing_audio_track_fails_instead_of_faking_transcription(tmp_path):
    with (
        patch.object(media, "FFMPEG_AVAILABLE", True),
        patch.object(media, "FFPROBE_AVAILABLE", True),
        patch.object(media, "probe_duration_seconds", return_value=65),
        patch.object(media.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "ffmpeg")),
        pytest.raises(RuntimeError, match="supported audio track"),
    ):
        media.extract_audio_segments("silent-video.mp4", str(tmp_path), segment_seconds=30)
