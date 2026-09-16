#!/bin/bash
# Run once, from the project root on the box:  sudo bash ops/services/install.sh
#
# Starts SearXNG, Whisper, the voice server and the media service at boot, so Alfred is ready
# whenever the box is on instead of waiting for listen.py to start them.
# listen.py and talk.py still work unchanged: they only start what is not
# already running.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
OWNER="${SUDO_USER:?run with sudo from your own account, not as root}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"
UNITS="alfred-searx alfred-whisper alfred-voice alfred-media"

echo "== 1/3 stopping the copies started by hand"
pkill -u "$OWNER" -f "^$PROJECT/.venv-rvc/bin/python $PROJECT/brain/voice_server.py" || true
pkill -u "$OWNER" -f "^$PROJECT/.venv-whisper/bin/python $PROJECT/brain/whisper_server.py" || true
pkill -u "$OWNER" -f "^.venv/bin/python -m searx.webapp" || true
pkill -u "$OWNER" -f "^$PROJECT/.venv-media/bin/python $PROJECT/brain/media_server.py" || true
sleep 3

echo "== 2/3 installing units for $OWNER in $PROJECT"
for unit in $UNITS; do
  sed -e "s|CHANGE_ME|$OWNER|" -e "s|CHANGE_PROJECT|$PROJECT|" \
    "$HERE/$unit.service" > "/etc/systemd/system/$unit.service"
done
systemctl daemon-reload
systemctl enable --now $UNITS

echo "== 3/3 waiting for them to answer"
for i in $(seq 90); do
  curl -sf 127.0.0.1:5051/health >/dev/null && curl -sf 127.0.0.1:5052/health >/dev/null && break
  sleep 2
done
for unit in $UNITS; do printf "   %-16s %s\n" "$unit" "$(systemctl is-active $unit)"; done
curl -sf 127.0.0.1:5051/health >/dev/null && echo "   voice answering" || echo "   voice NOT answering: journalctl -u alfred-voice -n 30"
curl -sf 127.0.0.1:5052/health >/dev/null && echo "   whisper answering" || echo "   whisper NOT answering: journalctl -u alfred-whisper -n 30"
