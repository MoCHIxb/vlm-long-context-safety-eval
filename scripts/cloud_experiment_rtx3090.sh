#!/usr/bin/env bash
# Independent Ubuntu22.04/Python3.12/Torch2.12.1/CUDA13.0 profile.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ACTION="${1:-help}"
if (($#)); then shift; fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="$ROOT/.cache/venvs/rtx3090"
export HF_HOME="$ROOT/.cache/huggingface"
export HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_XET=1 PYTHONUTF8=1
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 NUMEXPR_NUM_THREADS=8
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
case "$ACTION" in
  setup)
    # Reuse the image's torch without changing its base Python installation.
    "$PYTHON_BIN" -c 'import sys,torch; assert sys.version_info[:2]==(3,12), "Use the image Python 3.12"; assert torch.__version__.split("+")[0]=="2.12.1", "Image must provide PyTorch 2.12.1"; assert torch.version.cuda=="13.0", "Image torch must use CUDA 13.0"'
    "$PYTHON_BIN" -m venv --system-site-packages "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip
    "$VENV/bin/python" -m pip install --no-deps 'torchvision==0.27.1' \
      --index-url https://download.pytorch.org/whl/cu130
    "$VENV/bin/python" -m pip install -r requirements-cloud-rtx3090.txt \
      -c configs/cloud/rtx3090_constraints.txt
    "$VENV/bin/python" -m pip install --no-deps -e .
    "$VENV/bin/python" -m pip check
    mkdir -p outputs/cloud_rtx3090_environment
    "$VENV/bin/python" -m pip freeze > outputs/cloud_rtx3090_environment/pip-freeze.txt
    "$VENV/bin/python" scripts/cloud_runtime_rtx3090.py check
    ;;
  prepare|download|run|plan|check)
    if [[ ! -x "$VENV/bin/python" ]]; then
      echo 'Run: bash scripts/cloud_experiment_rtx3090.sh setup' >&2; exit 2
    fi
    "$VENV/bin/python" scripts/cloud_runtime_rtx3090.py "$ACTION" "$@"
    ;;
  *)
    echo 'Usage: bash scripts/cloud_experiment_rtx3090.sh {setup|prepare|download|plan|run|check}'
    echo 'Default serial models: llava7b then gemma3_12b (4864 each).'
    echo 'For Gemma: log in to HF on this server, then download --include-gated.'
    ;;
esac
