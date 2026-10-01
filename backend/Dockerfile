FROM python:3.14-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 trainu \
    && useradd --uid 10001 --gid 10001 --no-create-home trainu

WORKDIR /app
COPY requirements.txt .
# The CPU profile must not pull CUDA/cuDNN/NCCL merely because Torch is a
# transitive Sentence Transformers dependency. Install its official CPU wheel
# first; the pinned application requirements then reuse the satisfied version.
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.10.0+cpu" \
    && pip install -r requirements.txt
COPY --chown=trainu:trainu . .
RUN chmod +x docker-entrypoint.sh \
    && mkdir -p /var/cache/trainu/huggingface \
    && chown -R trainu:trainu /var/cache/trainu
USER 10001:10001
ENV HF_HOME=/var/cache/trainu/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 \
    WHISPER_MODEL_ID=dropbox-dash/faster-whisper-large-v3-turbo \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    WHISPER_CPU_THREADS=4
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl --fail --silent http://localhost:8000/health || exit 1
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["api"]
