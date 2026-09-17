#!/bin/bash
# Run once, from the project root on the box:  sudo bash ops/rgb/install.sh
#
# Makes the RGB memory glow solid red, now and at every boot. OpenRGB 1.0 is
# installed to /opt/openrgb from its official release (checksum pinned); its
# only missing system library on Ubuntu 24.04 is libopengl0.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
URL=https://codeberg.org/OpenRGB/OpenRGB/releases/download/release_1.0/OpenRGB_1.0_x86_64_81bbe18.AppImage
SHA256=a77d9fea9ab1e59e5ec2b5cec4ab22d50f0433594c4e83eb13de4e5c3cfadebf

echo "== 1/4 libopengl0"
apt-get install -y -q libopengl0 >/dev/null

echo "== 2/4 OpenRGB 1.0 into /opt/openrgb"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
curl -sSL -o "$work/OpenRGB.AppImage" "$URL"
echo "$SHA256  $work/OpenRGB.AppImage" | sha256sum -c --quiet
chmod +x "$work/OpenRGB.AppImage"
(cd "$work" && ./OpenRGB.AppImage --appimage-extract >/dev/null)
rm -rf /opt/openrgb && mv "$work/squashfs-root" /opt/openrgb && chmod 755 /opt/openrgb

echo "== 3/4 i2c-dev at boot"
echo i2c-dev > /etc/modules-load.d/i2c-dev.conf
modprobe i2c-dev

echo "== 4/4 red now and at every boot"
install -m 755 "$HERE/ram-color.sh" /usr/local/sbin/ram-color
install -m 644 "$HERE/ram-color.service" /etc/systemd/system/ram-color.service
systemctl daemon-reload
systemctl enable ram-color >/dev/null 2>&1
systemctl restart ram-color || true
journalctl -u ram-color -n 20 --no-pager -o cat | grep -v "^Starting\|^Finished\|^ram-color.service" || true
