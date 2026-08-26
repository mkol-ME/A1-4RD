#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1
export ALFRED_MEMORY_DB="${ALFRED_MEMORY_DB:-/srv/storage/alfred/memory.sqlite3}"

exec "$project_dir/.venv-rvc/bin/python" "$project_dir/voice_server.py"
