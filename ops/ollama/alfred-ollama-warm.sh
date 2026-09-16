#!/bin/bash
# Load whichever model alfred.py names, so the first reply after boot isn't a 20s model load.
# alfred.py has CRLF line endings (it round-trips through the Windows checkout), hence the tr.
M=$(tr -d '\r' < $HOME/a1-4rd/brain/alfred.py | sed -nE 's/^DEFAULT_MODEL = "(.*)"/\1/p')
[ -n "$M" ] || { echo "no DEFAULT_MODEL found"; exit 1; }
for _ in $(seq 60); do curl -sf http://localhost:11434/api/version >/dev/null && break; sleep 2; done
curl -sf http://localhost:11434/api/generate -d "{\"model\":\"$M\",\"keep_alive\":-1}" >/dev/null && echo "loaded $M"
