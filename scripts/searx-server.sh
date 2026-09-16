#!/usr/bin/env bash
set -euo pipefail

# Local metasearch for Alfred's search_web tool. Bound to localhost: the only
# client is the voice server on this machine, and a public SearXNG instance
# would be a very different thing to run.
export SEARXNG_SETTINGS_PATH="${SEARXNG_SETTINGS_PATH:-$HOME/searxng-config/settings.yml}"
cd "$HOME/searxng"
exec .venv/bin/python -m searx.webapp
