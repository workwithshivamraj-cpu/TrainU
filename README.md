# TrainU

A workspace for turning approved training videos and documents into answers with source citations. Teams organize knowledge by application, review uploads, and ask questions against their organization's approved library.

The product includes an Angular workspace, FastAPI API, PostgreSQL with pgvector, a Celery ingestion worker, Redis, private S3-compatible media storage, and a Chrome/Edge companion extension. The interface uses a light, restrained design with role-aware actions and a documentation center.

**Release status:** the repository provides an implementation and deployment profile for a controlled pilot. A production domain, infrastructure, real AI credentials, operator policies, and the release gates in [the launch checklist](docs/launch-checklist.md) must be completed before customer launch. Payment collection, enterprise SSO, and compliance certifications are not included. Mock mode demonstrates the flow and does not transcribe arbitrary videos.

## Run locally

Requires Docker Engine/Desktop with Compose v2. Docker will download the necessary images; AI API credentials are unnecessary for the demo.

```bash
make setup
make up
docker compose run --rm backend seed
```

`make up` takes a private local database and object-storage snapshot before the migration job. See [runtime profiles](docs/runtime-profiles.md) and run `make doctor PROFILE=poc` before testing real AI/media dependencies.

Open `http://localhost:4200`. API reference: `http://localhost:8000/api/v1/docs`. Object-storage console: `http://localhost:9001` (local only). Services bind to loopback, and database/storage volumes survive `docker compose down`.

The seed creates sample tenants and approved content. The following accounts use `TrainU_Demo123!` and are for local demonstration only:

| Role | Email |
|---|---|
| Organization admin | admin@portfolioteam.example |
| Content owner | owner@portfolioteam.example |
| Contributor | contributor@portfolioteam.example |
| Viewer | viewer@portfolioteam.example |

The platform-flag demo account is `platform.admin@trainu.dev`; platform administration currently has no separate management console. By default, the seed generates a test video with ffmpeg. Set `TRAINU_DEMO_VIDEO=/absolute/path/to/video.mp4` (or `.mov`) when running the seed to store a supplied local sample. Mock mode creates a clearly marked placeholder transcript for uploaded videos; it does not perform speech recognition.

Real video ingestion requires a decodable MP4/MOV/M4V/WEBM file with an audio track, FFmpeg/ffprobe, and a configured speech-to-text provider. Audio is split into timestamped segments (10 minutes by default), then transcripts are chunked and embedded in bounded batches. The configured LLM runs when users ask questions against approved evidence. Provider, file, and deployment limits mean this cannot guarantee that every video works. See [deployment](docs/deployment.md) and [QA](docs/qa.md) for staging requirements.

Confirm additional sample accounts in `backend/scripts/seed.py`. Never seed a live deployment or import demo credentials into it. Create your first workspace with the registration screen instead.

## Everyday flow

1. Register a workspace and invite teammates with the smallest suitable role.
2. Create an application and optional modules.
3. A contributor or content owner uploads a video or document and watches processing progress.
4. Review the transcript, correct it, and approve the source.
5. Ask a question; inspect the quoted evidence and open its source or timestamp.
6. Archive outdated knowledge, review feedback, and use the audit log for administration.

Source access and assistant retrieval depend on organization membership, approval state, and source audience. The API enforces permissions independently of the interface.

## Browser extension

Load the `extension/` folder through Chrome/Edge's **Extensions → Developer mode → Load unpacked**. Set the TrainU workspace URL in extension settings. Selected text can be sent to the workspace as a draft question; the user submits it explicitly. See [extension instructions](extension/README.md) for permissions and packaging. Store publication is a separate release step.

## Verify

```bash
make test                    # disposable trainu_test database; never point at live data
make smoke                   # frontend, API auth boundary and cache headers
cd frontend
npm ci
npx playwright install chromium
npm run e2e                  # requires running, seeded local stack
npm run build -- --configuration production
```

The GitHub Actions workflow runs dependency security audits, Python correctness lint, production frontend build, full-stack integration tests and browser acceptance tests. See [QA](docs/qa.md) for what these checks establish and the manual release gates.

## Deploy and operate

[Deployment](docs/deployment.md) explains the separate production Compose profile, managed PostgreSQL/Redis/S3, secrets, TLS and CDN caching. API and ingestion scale independently; the supplied Compose profile is a single-host starting point, not a managed autoscaling cluster. [Architecture](docs/architecture.md) explains the scale boundaries and data model. [Operations](docs/operations.md) covers migrations, rollback, backups, recovery and incidents.

## Product and operating documents

The app's **Help & docs** area exposes these documents:

- [Product and roles](docs/product.md)
- [Architecture and scale](docs/architecture.md)
- [API reference](docs/api.md)
- [Deployment and CDN](docs/deployment.md)
- [Operations and recovery](docs/operations.md)
- [Security model](docs/security.md)
- [QA and acceptance](docs/qa.md)
- [Launch checklist](docs/launch-checklist.md)
- [Commercial packaging](docs/commercial.md)
- [Privacy notice draft](docs/privacy.md)
- [Terms draft](docs/terms.md)
- [Delivery backlog](docs/plan.md)

Privacy and terms are operator drafts with explicit open fields. They must be completed for the actual business and service before publication as binding customer policies.
