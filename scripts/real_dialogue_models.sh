#!/usr/bin/env bash
# Explicitly select one existing RTX3090 model environment; never starts a queue.
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUTF8=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="${REAL_DIALOGUE_PYTHON:-$PWD/.cache/venvs/rtx3090/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  echo 'Existing model Python missing; set REAL_DIALOGUE_PYTHON to the Python used for the original LLaVA/Gemma run.' >&2
  exit 2
fi
exec "$PYTHON" scripts/run_real_dialogue_models.py "$@"
