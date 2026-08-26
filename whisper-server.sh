#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
site_packages="$project_dir/.venv-whisper/lib/python3.12/site-packages"

# GPU 1 is the GTX 1060, shared with RVC. GPU 0 remains dedicated to Ollama.
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1
export LD_LIBRARY_PATH="$site_packages/nvidia/cublas/lib:$site_packages/nvidia/cudnn/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec "$project_dir/.venv-whisper/bin/python" "$project_dir/whisper_server.py"
