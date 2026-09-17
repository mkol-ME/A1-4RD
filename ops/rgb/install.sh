#!/bin/bash
# Run once, from the project root on the box:  sudo bash ops/rgb/install.sh
#
# Makes the RGB memory glow solid red, now and at every boot, with one small
# Python script and no other software. Also removes the OpenRGB install this
# replaced, if it is there.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ -d /opt/openrgb ]; then
  echo "== removing OpenRGB"
  rm -rf /opt/openrgb /var/lib/openrgb
  apt-get remove -y -q libopengl0 >/dev/null || true
fi

echo "== i2c-dev at boot"
echo i2c-dev > /etc/modules-load.d/i2c-dev.conf
modprobe i2c-dev

echo "== red now and at every boot"
install -m 755 "$HERE/ram-color.py" /usr/local/sbin/ram-color
install -m 644 "$HERE/ram-color.service" /etc/systemd/system/ram-color.service
systemctl daemon-reload
systemctl enable ram-color >/dev/null 2>&1
/usr/local/sbin/ram-color --probe || true
systemctl restart ram-color || true
journalctl -u ram-color -n 6 --no-pager -o cat | grep -v "^Starting\|^Finished\|^ram-color.service" || true
