#!/usr/bin/env bash
set -euo pipefail

# YouTube search and audio for playing music through Alfred's speaker. Its own
# environment (yt-dlp, PyAV) so the voice server's pinned packages stay put.
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# His wording lives beside his memory on the array, not in the checkout. If the
# array is not there, the code falls back to the stand-ins in persona/.
export ALFRED_PERSONA_DIR="${ALFRED_PERSONA_DIR:-/srv/storage/alfred/persona}"

exec "$project_dir/.venv-media/bin/python" "$project_dir/brain/media_server.py"
