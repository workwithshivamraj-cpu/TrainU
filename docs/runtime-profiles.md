# TrainU runtime profiles

TrainU has three intentionally separate runtime paths. None is an assurance that an external service is production ready.

## Deterministic demo

The default `make up` stack reads the root `.env`, uses local PostgreSQL, Redis and RustFS, and keeps mock AI providers for repeatable seeded demos and tests. The UI and answer metadata should make simulated AI visible. This profile is not suitable for evaluating arbitrary uploads or model answer quality.

```bash
make setup
make up
make doctor PROFILE=demo
```

`make up` starts only the stateful services first, pauses API/worker writers, writes a private database and object-store snapshot to the ignored `.local-backups/` directory, and then runs the migration job. Direct migration jobs refuse to run unless the caller supplies the one-shot confirmation after verifying a backup. Keep the backup private; it can contain customer material. This local backup is not encrypted or off-host and is not a production backup policy.

## Local real-AI proof of concept

The existing host-run API reads `backend/.env` from the `backend/` working directory and connects to Ollama through loopback. Qwen2.5 7B is locked in [model-lock.json](../infrastructure/model-lock.json) to the digest observed on this host; generation uses temperature 0.1, top-p 0.9, 768 output tokens and seed 42. The faster-whisper `1.2.1` and Sentence Transformers `6.1.0` packages are pinned in `backend/requirements.txt`; model repository revisions are immutable commit IDs in the lock file. To avoid modifying the running demo's environment, the optional host setup uses `backend/.venv-poc` and `.local-models/huggingface`; a container alternative stores model files in the persistent `trainu_model_cache` volume. The ARM64 image explicitly installs PyTorch's CPU wheel before AI requirements, avoiding CUDA libraries. It measures about 3.01 GB (Python/AI layer 1.66 GB; media/OCR layer 489 MB), so reducing and splitting the worker image remains a packaging task. The current all-minilm vectors are an interim profile; replace them as a separate generation before enabling E5 retrieval. The E5 model card documents multilingual support and task prefixes; use its query/document APIs and pass application QA: [E5 model card](https://huggingface.co/intfloat/multilingual-e5-small), [faster-whisper releases](https://github.com/SYSTRAN/faster-whisper/releases), [Sentence Transformers releases](https://github.com/huggingface/sentence-transformers/releases).

Keep Ollama bound to loopback. Do not expose its port to a LAN or public interface. Confirm that `DATABASE_URL`, `REDIS_URL` and S3 settings in `backend/.env` point to local TrainU services before starting the host API. `make doctor PROFILE=poc` checks host tools, OCR languages, local Mailpit/ClamAV, Ollama model digest and required local model caches without printing secrets. Missing requirements are an expected failure until P07/P09 land.

```bash
make up                         # local data services + deterministic containers
make doctor PROFILE=poc         # report local media/model prerequisites
make install-poc                 # isolated Python 3.12 environment for local AI work
make models-poc                  # download only immutable revisions into ignored .local-models/
make models-container            # download immutable revisions into the Compose model volume
cd backend && .venv-poc/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

The ARM64 backend image and both cached models were verified on 2026-09-29. An offline E5 encode returned normalized 384-dimensional vectors, and faster-whisper produced 11 English segments from the synthetic 58.5-second ClientVantage MP4 using CPU INT8. These are runtime smoke tests, not evidence of language-level quality or end-to-end arbitrary-upload processing; P07/P09 must connect and validate them in the application. During the smoke checks, the host had 2.6 GiB available RAM. Keep concurrency bounded and watch Docker Desktop memory; do not start multiple model workers on this machine.

The `local-tools` Compose profile started by `make up` runs Mailpit on loopback ports 1025/8025. The separate `scanner` profile starts ClamAV only on the private Compose network with the official image's daemon-health probe; use `make scanner-up` and `make doctor PROFILE=scanner` when validating that optional service. The pinned ClamAV image currently publishes only linux/amd64, so this Apple Silicon host would use Docker emulation; its scan path has not been run here. The application does not yet route account mail through Mailpit or scan uploads with ClamAV; those integrations land with P03 and P06. A healthy tool container alone does not prove either integration.

Use a separate terminal for the worker. Do not run database migrations against a populated local volume until a database and object-data backup is available and verified.

## Production configuration (not launchable yet)

`docker-compose.production.yml` accepts immutable image references and an operator-managed env file. `.env.production.example` is a template only and intentionally cannot run. The settings validator rejects mock providers, demo mode, weak secrets, in-memory rate limiting and non-TLS public storage URLs. The migration container also requires an operator-supplied backup confirmation after the configured backup/restore process. A passing configuration check is not a deployment, a real billing/email integration, a backup restore drill, a security certification or a launch approval.

```bash
make doctor PROFILE=production
```

Do not store real deployment values in the repository. Public deployment and live transactions remain explicit external launch decisions.
