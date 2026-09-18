#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=0
# His wording lives beside his memory on the array, not in the checkout. If the
# array is not there, the code falls back to the stand-ins in persona/.
export ALFRED_PERSONA_DIR="${ALFRED_PERSONA_DIR:-/srv/storage/alfred/persona}"
export ALFRED_MEMORY_DB="${ALFRED_MEMORY_DB:-/srv/storage/alfred/memory.sqlite3}"
# One-stage distilled voice candidate. Unset this variable to fall back to the
# original Piper -> RVC chain without deleting either model.
export ALFRED_PIPER_MODEL="${ALFRED_PIPER_MODEL:-$project_dir/voice-audition-distilled/epoch18.onnx}"

exec "$project_dir/.venv-rvc/bin/python" "$project_dir/brain/voice_server.py"
