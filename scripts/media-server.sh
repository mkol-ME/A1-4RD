#!/usr/bin/env bash
set -euo pipefail

# YouTube search and audio for playing music through Alfred's speaker. Its own
# environment (yt-dlp, PyAV) so the voice server's pinned packages stay put.
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$project_dir/.venv-media/bin/python" "$project_dir/brain/media_server.py"
