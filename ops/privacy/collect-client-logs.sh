#!/usr/bin/env bash
# Put the client's playback evidence where it belongs: on the array, and
# nowhere else. The log lines carry what he said, so they are a conversation
# record, and a conversation record lives on his own server only.
#
#   bash ops/privacy/collect-client-logs.sh            # send, verify, then delete locally
#   ALFRED_CLIENT_LOGS=/some/dir bash ops/privacy/collect-client-logs.sh
set -euo pipefail

host="${ALFRED_HOST:-a1-4rd}"
logs="${ALFRED_CLIENT_LOGS:-${LOCALAPPDATA:-$HOME/.cache}/A1-4RD/logs}"
stamp="$(date +%Y-%m-%d)"
remote="/srv/storage/alfred/client-logs/$stamp"

if [ ! -d "$logs" ]; then
    echo "nothing to collect: $logs does not exist"
    exit 0
fi

lines=$(wc -l < "$logs/audio.log" 2>/dev/null || echo 0)
clips=$(ls "$logs/clips" 2>/dev/null | wc -l || echo 0)
echo "sending $lines log lines and $clips clips to $host:$remote"

ssh "$host" "mkdir -p '$remote' && chmod 700 '$remote'"
tar czf - -C "$(dirname "$logs")" "$(basename "$logs")" \
    | ssh "$host" "cd '$remote' && tar xzf - && chmod -R go-rwx ."

there=$(ssh "$host" "cd '$remote/$(basename "$logs")' && echo \"\$(wc -l < audio.log) \$(ls clips | wc -l)\"")
if [ "$lines $clips" = "$there" ]; then
    rm -rf "$logs"
    echo "verified on the array, removed the local copy"
else
    echo "MISMATCH: local '$lines $clips' vs array '$there' — local copy kept" >&2
    exit 1
fi
