#!/usr/bin/env bash
# Read-only local preflight. It never prints environment variables or credentials.
set -uo pipefail

profile="${1:-demo}"
case "$profile" in
  demo|poc|production|scanner) ;;
  *) echo "Usage: scripts/doctor.sh [demo|poc|production|scanner]" >&2; exit 2 ;;
esac

failed=0
check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    printf 'OK   %s found\n' "$1"
  else
    printf 'MISS %s is not installed\n' "$1"
    failed=1
  fi
}

echo "TrainU local preflight — profile: $profile"
for utility in docker bash; do check_command "$utility"; done
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo 'OK   Docker Compose is available'
else
  echo 'MISS Docker Compose plugin is unavailable'
  failed=1
fi

python3 - <<'PY'
from pathlib import Path
import platform
import re
import shutil
import subprocess

total = available = None
if platform.system() == "Darwin":
    try:
        total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        page_size = int(subprocess.check_output(["sysctl", "-n", "hw.pagesize"], text=True).strip())
        vm = subprocess.check_output(["vm_stat"], text=True)
        pages = sum(
            int(value.replace(".", ""))
            for name, value in re.findall(r"Pages (free|inactive|speculative|purgeable):\s+([0-9.]+)", vm)
        )
        available = pages * page_size
    except (OSError, ValueError, subprocess.CalledProcessError):
        pass
elif Path("/proc/meminfo").exists():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            total = int(line.split()[1]) * 1024
        elif line.startswith("MemAvailable:"):
            available = int(line.split()[1]) * 1024
if total is not None:
    print(f"INFO memory_total_gib={total / (1024 ** 3):.1f}")
if available is not None:
    print(f"INFO memory_available_gib={available / (1024 ** 3):.1f}")
disk = shutil.disk_usage(Path.cwd()).free
print(f"INFO workspace_disk_free_gib={disk / (1024 ** 3):.1f}")
PY

check_tool_in_runtime() {
  if command -v "$1" >/dev/null 2>&1; then
    printf 'OK   %s is installed on the host\n' "$1"
  elif [[ "$profile" != poc ]] && docker compose exec -T backend sh -c "command -v '$1'" >/dev/null 2>&1; then
    printf 'OK   %s is installed in the backend container\n' "$1"
  elif docker image inspect trainu-backend:latest >/dev/null 2>&1 \
      && docker run --rm --network none --entrypoint sh trainu-backend:latest -c "command -v '$1'" >/dev/null 2>&1; then
    printf 'OK   %s is installed in the built backend image\n' "$1"
  else
    printf 'MISS %s is not available on the host or running backend\n' "$1"
    failed=1
  fi
}

if [[ "$profile" == demo || "$profile" == poc ]]; then
  for utility in ffmpeg ffprobe tesseract curl; do check_tool_in_runtime "$utility"; done
  if command -v tesseract >/dev/null 2>&1; then
    languages="$(tesseract --list-langs 2>/dev/null || true)"
    for language in eng hin; do
      if printf '%s\n' "$languages" | grep -Fxq "$language"; then
        printf 'OK   Tesseract language %s available on host\n' "$language"
      else
        printf 'MISS Tesseract language %s unavailable on host\n' "$language"
        failed=1
      fi
    done
  elif [[ "$profile" != poc ]] && docker compose exec -T backend tesseract --list-langs 2>/dev/null | grep -Fxq eng \
      && docker compose exec -T backend tesseract --list-langs 2>/dev/null | grep -Fxq hin; then
    echo 'OK   backend Tesseract has English and Hindi data'
  elif docker image inspect trainu-backend:latest >/dev/null 2>&1 \
      && docker run --rm --network none --entrypoint tesseract trainu-backend:latest --list-langs 2>/dev/null | grep -Fxq eng \
      && docker run --rm --network none --entrypoint tesseract trainu-backend:latest --list-langs 2>/dev/null | grep -Fxq hin; then
    echo 'OK   built backend image Tesseract has English and Hindi data'
  else
    echo 'MISS backend Tesseract needs both eng and hin data'
    failed=1
  fi
  if curl --silent --show-error --fail --max-time 2 http://127.0.0.1:8025/readyz >/dev/null 2>&1; then
    echo 'OK   local Mailpit readiness endpoint responds'
  else
    echo 'MISS local Mailpit is not ready at 127.0.0.1:8025/readyz'
    failed=1
  fi
fi

if [[ "$profile" == scanner ]]; then
  clamav_id="$(docker compose --profile scanner ps -q clamav 2>/dev/null || true)"
  if [[ -n "$clamav_id" ]] && docker inspect --format '{{.State.Health.Status}}' "$clamav_id" 2>/dev/null | grep -Fxq healthy; then
    echo 'OK   local ClamAV daemon responds'
  else
    echo 'MISS local ClamAV is not ready; run make scanner-up and check startup/signature data'
    failed=1
  fi
fi

if [[ "$profile" == poc ]]; then
  check_command ollama
  if command -v ollama >/dev/null 2>&1; then
    models="$(ollama list 2>/dev/null | awk 'NR>1 {print $1}' || true)"
    if printf '%s\n' "$models" | grep -Fxq qwen2.5:7b; then
      echo 'OK   Ollama model qwen2.5:7b is present'
    else
      echo 'MISS Ollama model qwen2.5:7b is not present'
      failed=1
    fi
    if curl --silent --show-error --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      echo 'OK   Ollama API responds on loopback'
      if python3 - <<'PY' >/dev/null 2>&1
import json
from pathlib import Path
from urllib.request import urlopen

lock = json.loads(Path("infrastructure/model-lock.json").read_text())
expected = lock["answer_model"]["digest"]
with urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
    models = json.load(response).get("models", [])
actual = next((item.get("digest") for item in models if item.get("name") == "qwen2.5:7b"), None)
if actual != expected:
    raise SystemExit(1)
PY
      then
        echo 'OK   Ollama Qwen digest matches the checked-in model lock'
      else
        echo 'MISS Ollama Qwen digest does not match infrastructure/model-lock.json'
        failed=1
      fi
    else
      echo 'MISS Ollama API is not responding on loopback 127.0.0.1:11434'
      failed=1
    fi
  fi

  py="backend/.venv-poc/bin/python"
  if [[ ! -x "$py" ]]; then
    py="python3.12"
    command -v "$py" >/dev/null 2>&1 || py="python3"
  fi
  for package in faster_whisper sentence_transformers; do
    if "$py" -c "import $package" >/dev/null 2>&1; then
      printf 'OK   Python package %s is installed\n' "$package"
    elif docker image inspect trainu-backend:latest >/dev/null 2>&1 \
        && docker run --rm --network none --entrypoint python trainu-backend:latest -c "import $package" >/dev/null 2>&1; then
      printf 'OK   Python package %s is installed in the built backend image\n' "$package"
    else
      printf 'MISS Python package %s is not installed\n' "$package"
      failed=1
    fi
  done
  if HF_HOME="$PWD/.local-models/huggingface" "$py" scripts/check-model-cache.py embedding_model >/dev/null 2>&1; then
    echo 'OK   multilingual-e5-small model is cached'
  elif docker image inspect trainu-backend:latest >/dev/null 2>&1 \
      && docker compose run --rm --no-deps -e HF_HOME=/var/cache/trainu/huggingface -e TRAINU_MODEL_LOCK=/tmp/model-lock.json \
        -v "$PWD/scripts/check-model-cache.py:/tmp/check-model-cache.py:ro" \
        -v "$PWD/infrastructure/model-lock.json:/tmp/model-lock.json:ro" \
        --entrypoint python backend /tmp/check-model-cache.py embedding_model >/dev/null 2>&1; then
    echo 'OK   multilingual-e5-small model is cached in the backend model volume'
  else
    echo 'MISS multilingual-e5-small model files are not cached locally'
    failed=1
  fi
  if HF_HOME="$PWD/.local-models/huggingface" "$py" scripts/check-model-cache.py transcription_model >/dev/null 2>&1; then
    echo 'OK   faster-whisper large-v3-turbo model is cached'
  elif docker image inspect trainu-backend:latest >/dev/null 2>&1 \
      && docker compose run --rm --no-deps -e HF_HOME=/var/cache/trainu/huggingface -e TRAINU_MODEL_LOCK=/tmp/model-lock.json \
        -v "$PWD/scripts/check-model-cache.py:/tmp/check-model-cache.py:ro" \
        -v "$PWD/infrastructure/model-lock.json:/tmp/model-lock.json:ro" \
        --entrypoint python backend /tmp/check-model-cache.py transcription_model >/dev/null 2>&1; then
    echo 'OK   faster-whisper large-v3-turbo model is cached in the backend model volume'
  else
    echo 'MISS faster-whisper large-v3-turbo model files are not cached locally'
    failed=1
  fi
fi

if [[ "$profile" == production ]]; then
  echo 'INFO Production mode also needs TLS, real providers, live email/billing, backups, legal and support configuration.'
  if [[ ! -f .env.production ]]; then
    echo 'MISS .env.production is absent (the committed file is only a template)'
    failed=1
  elif ! docker compose --env-file .env.production -f docker-compose.production.yml config -q >/dev/null 2>&1; then
    echo 'MISS production configuration is incomplete or invalid'
    failed=1
  else
    echo 'OK   production Compose configuration parses'
  fi
fi

if (( failed )); then
  echo 'Preflight incomplete. Install/fix the items above before starting this profile.'
  exit 1
fi
echo 'Preflight checks passed. This does not replace application, model-quality or security acceptance.'
