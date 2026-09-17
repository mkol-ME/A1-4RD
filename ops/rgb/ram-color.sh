#!/bin/bash
# Sets every RGB memory stick OpenRGB finds to one static colour (default red).
# Run as root: the sticks' light controllers sit on the SMBus, and /dev/i2c-* is root-only.
#
#   ram-color            # red
#   ram-color 00FF00     # any hex colour
#
# Only DRAM devices are touched. The Corsair Vengeance LPX sticks have no
# lights and are not listed; the G.Skill Trident Z RGB pair is.
set -uo pipefail
COLOR="${1:-FF0000}"
OPENRGB=/opt/openrgb/AppRun
export HOME=/var/lib/openrgb QT_QPA_PLATFORM=offscreen
mkdir -p "$HOME"

listing="$("$OPENRGB" --noautoconnect --list-devices 2>&1)"
# "0: G.Skill Trident Z RGB" followed a few lines later by "  Type: DRAM"
sticks="$(awk '/^[0-9]+: /{index_=$1; sub(":","",index_)} /^[[:space:]]*Type:/ && /DRAM/ {print index_}' <<<"$listing")"
if [ -z "$sticks" ]; then
  echo "no RGB memory found. OpenRGB saw:"
  echo "$listing"
  exit 1
fi
status=0
for stick in $sticks; do
  name="$(grep -m1 "^$stick: " <<<"$listing")"
  if "$OPENRGB" --noautoconnect --device "$stick" --mode static --color "$COLOR" >/dev/null 2>&1; then
    echo "set $name to #$COLOR"
  else
    echo "FAILED on $name"; status=1
  fi
done
exit $status
