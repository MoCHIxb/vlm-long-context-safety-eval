#!/usr/bin/env bash
# Reuse the existing Qwen3 environment; no installs, downloads or other models.
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUTF8=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="${REAL_DIALOGUE_PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  for candidate in "$PWD/.venv-cloud/bin/python" "$PWD/.cache/venvs/rtx3090/bin/python"; do
    if [[ -x "$candidate" ]]; then PYTHON="$candidate"; break; fi
  done
fi
if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
  echo 'Existing Qwen3 Python not found. Set REAL_DIALOGUE_PYTHON to the Python used for your original Qwen3 run.' >&2
  exit 2
fi
exec "$PYTHON" scripts/run_real_dialogue_supplement.py "$@"
