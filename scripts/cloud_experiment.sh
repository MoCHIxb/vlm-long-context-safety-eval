#!/usr/bin/env bash
# Linux single-GPU setup/download/run entry point; no sudo or credential copying.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ACTION="${1:-help}"
if (($#)); then shift; fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
export HF_HOME="${HF_HOME:-$ROOT/.cache/huggingface}"
export HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_XET=1 PYTHONUTF8=1
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
case "$ACTION" in
  setup)
    "$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
    "$PYTHON_BIN" -m venv .venv-cloud
    .venv-cloud/bin/python -m pip install --upgrade pip
    # Set TORCH_INDEX_URL for the server's CUDA wheel source; no silent CPU fallback.
    .venv-cloud/bin/python -m pip install 'torch==2.14.1' 'torchvision==0.29.1' \
      --index-url "${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
    .venv-cloud/bin/python -m pip install -r requirements-cloud.txt
    .venv-cloud/bin/python -m pip install --no-deps -e .
    .venv-cloud/bin/python -m pip check
    mkdir -p outputs/cloud_environment
    .venv-cloud/bin/python -m pip freeze > outputs/cloud_environment/pip-freeze.txt
    .venv-cloud/bin/python scripts/cloud_runtime.py check
    ;;
  prepare|download|run|plan|check)
    if [[ ! -x .venv-cloud/bin/python ]]; then
      echo 'Run: bash scripts/cloud_experiment.sh setup' >&2; exit 2
    fi
    .venv-cloud/bin/python scripts/cloud_runtime.py "$ACTION" "$@"
    ;;
  *)
    echo 'Usage: bash scripts/cloud_experiment.sh {setup|prepare|download|plan|run|check}'
    echo 'Default cloud model: qwen3vl8b. Repeat --model to queue multiple models serially.'
    echo 'Gemma: log in on this server with HF_HOME set, then pass --include-gated to download.'
    ;;
esac
