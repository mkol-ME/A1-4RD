#!/bin/sh
set -eu
cd "$(dirname "$0")"
command -v dtc >/dev/null 2>&1 || { echo 'Install device-tree-compiler on the Pi first.' >&2; exit 1; }
dtc -@ -I dts -O dtb -o alfred-audio.dtbo alfred-audio-overlay.dts
test -s alfred-audio.dtbo
echo 'Built alfred-audio.dtbo. Follow README.md to install; nothing was installed automatically.'
