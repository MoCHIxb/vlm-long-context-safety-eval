#!/usr/bin/env bash
# Linux/NVIDIA: reuse the existing verified RTX3090 environment; one model per process.
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
export HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUTF8=1
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="${FREE_HISTORY_PYTHON:-$PWD/.cache/venvs/rtx3090/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  echo 'Existing RTX3090 environment missing; use scripts/cloud_experiment_rtx3090.sh setup first.' >&2
  exit 2
fi
exec "$PYTHON" scripts/run_free_history_supplement.py "$@"
