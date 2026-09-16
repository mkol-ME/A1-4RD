#!/usr/bin/env bash
# A throwaway copy of the voice server for test turns, beside the real one.
#
#   scripts/voice-test-server.sh start   # port 5061, on a snapshot of memory
#   scripts/voice-test-server.sh stop
#
# The real service on 5051 keeps running under systemd. Stopping it for tests
# used to leave it stopped: a clean exit is not a failure, so systemd never
# brought it back.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
port=5061
db=/tmp/alfred-test-memory.sqlite3
pidfile=/tmp/alfred-voice-test.pid
log="$project_dir/rvc-output/voice-test-server.log"

case "${1:-}" in
  start)
    [ -f "$pidfile" ] && kill "$(cat "$pidfile")" 2>/dev/null || true
    rm -f "$db" "$db-wal" "$db-shm"
    python3 -c "import sqlite3; sqlite3.connect('/srv/storage/alfred/memory.sqlite3').backup(sqlite3.connect('$db'))"
    ALFRED_MEMORY_DB="$db" ALFRED_VOICE_PORT="$port" setsid -f "$project_dir/scripts/voice-server.sh" > "$log" 2>&1
    for _ in $(seq 60); do
      curl -sf "127.0.0.1:$port/health" >/dev/null && break
      sleep 2
    done
    pid="$(pgrep -f "^$project_dir/.venv-rvc/bin/python $project_dir/brain/voice_server.py" \
           | while read -r p; do tr '\0' '\n' < "/proc/$p/environ" | grep -qx "ALFRED_VOICE_PORT=$port" && echo "$p"; done)"
    echo "$pid" > "$pidfile"
    echo "test voice server on 127.0.0.1:$port (pid $pid, memory $db)"
    ;;
  stop)
    [ -f "$pidfile" ] && kill "$(cat "$pidfile")" 2>/dev/null && echo "stopped" || echo "not running"
    rm -f "$pidfile"
    ;;
  *)
    echo "usage: $0 start|stop" >&2
    exit 2
    ;;
esac
