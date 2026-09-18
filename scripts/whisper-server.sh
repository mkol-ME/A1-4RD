#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
site_packages="$project_dir/.venv-whisper/lib/python3.12/site-packages"

# The GTX 1060 is the only CUDA card since the 2080 Super left (2026-09-16), so it
# is device 0. Ollama runs on the MI50 over Vulkan and never touches CUDA.
export CUDA_DEVICE_ORDER=PCI_BUS_ID
# His wording lives beside his memory on the array, not in the checkout. If the
# array is not there, the code falls back to the stand-ins in persona/.
export ALFRED_PERSONA_DIR="${ALFRED_PERSONA_DIR:-/srv/storage/alfred/persona}"
export CUDA_VISIBLE_DEVICES=0
export LD_LIBRARY_PATH="$site_packages/nvidia/cublas/lib:$site_packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec "$project_dir/.venv-whisper/bin/python" "$project_dir/brain/whisper_server.py"
