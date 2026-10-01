# TrainU demo motion videos

The local demo library includes four narrated motion-graphic videos. Each file follows the matching ClientVantage or SupplyLine training transcript already attached to its source, and the transcript chunk timestamps are aligned to the rendered clip duration.

| Source | Duration | Local file |
| --- | ---: | --- |
| ClientVantage — Creating a New Client Account | 58.5 s | `artifacts/demo-videos/clientvantage_create.mp4` |
| ClientVantage — Updating Client Account Status | 54.1 s | `artifacts/demo-videos/clientvantage_status.mp4` |
| SupplyLine — Creating a Purchase Order | 51.8 s | `artifacts/demo-videos/supplyline_create.mp4` |
| SupplyLine — Approving and Updating Purchase Order Status | 48.3 s | `artifacts/demo-videos/supplyline_status.mp4` |

## What these videos are

- Clean, light 16:9 motion graphics with a TrainU mark, simulated product screens, animated step cards, progress indicators, and spoken walkthroughs.
- The narration uses macOS's built-in Samantha text-to-speech voice. The visuals are illustrative, not screen recordings of ClientVantage or SupplyLine.
- These are demonstration assets. The sample applications and workflows are fictional and must not be presented as recordings of a customer's actual systems.
- The seeded transcript uses scripted demo content. The local host API uses Ollama/Qwen2.5 7B for answer synthesis and all-minilm for semantic search; new video ingestion still uses mock transcription/embeddings unless its worker is separately configured. Replacing a file does not make the app transcribe arbitrary uploaded videos. The production code path extracts/transcribes/chunks/embeds uploads, but needs real providers and must be validated in staging.
- The bounded excerpt player includes Mute/Unmute and Stop controls. Stop pauses and rewinds to the selected excerpt's start; the mute toggle leaves playback running.

## Regenerate and attach to the local demo

On macOS with FFmpeg/ffprobe installed, the TrainU virtual environment, and local PostgreSQL/Redis/RustFS services available, run:

```sh
PYTHONPATH=backend backend/.venv/bin/python scripts/create_demo_motion_videos.py
```

The script renders the MP4s and voice tracks into `artifacts/demo-videos/`, then replaces the matching seeded source objects in the configured local S3-compatible bucket and updates their media metadata and transcript chunk times. It removes the old placeholder objects after the replacements are saved. Do not point this script at production storage.

To seed a clean local demo database with these individual matching video files, mount this directory into the backend container and pass `TRAINU_DEMO_VIDEO_CLIENTVANTAGE_CREATE`, `TRAINU_DEMO_VIDEO_CLIENTVANTAGE_STATUS`, `TRAINU_DEMO_VIDEO_SUPPLYLINE_CREATE`, and `TRAINU_DEMO_VIDEO_SUPPLYLINE_STATUS` paths. The seeder validates each MP4/MOV and matches it to its corresponding transcript instead of assigning the same clip to every source.

## Motion MCP note

The Motion MCP connected in this environment exposes documentation/example search, not a video-rendering endpoint. Its animation references were checked; the final video frames and H.264/AAC MP4 files were rendered locally with Swift, CoreGraphics, AVFoundation, and macOS text-to-speech.
