#!/bin/bash
# Find a quieter minimum speed for the MI50 fan, then optionally save it.
#   sudo bash ops/fan/find-floor.sh
#
# install-fan.sh measured the floor in coarse steps (…128, 100, 80) and the fan
# stalled at 80, so it settled on 100 + 10 = 110 (about 3,100 rpm). Somewhere
# between 80 and 110 there may be a setting that still spins steadily and is
# quieter. This walks down in small steps from above, the way mi50-fan itself
# eases off, and at each one holds for 20 s and records the slowest and fastest
# rpm it saw. A step that sags below MIN_RPM or wobbles more than WOBBLE_PCT is
# where it stops. The recommendation is the lowest steady step plus a margin.
#
# Safe to interrupt: mi50-fan is restarted on exit, whatever happens. It also
# stops early if the GPU junction reaches 55C (at rest it sits near 30C).
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }

CONF=/etc/mi50-fan.conf
CHIP=$(python3 -c "import json; print(json.load(open('$CONF'))['chip'])")
PWM_N=$(python3 -c "import json; print(json.load(open('$CONF'))['pwm'])")
CURRENT_MIN=$(python3 -c "import json; print(json.load(open('$CONF'))['min_pwm'])")
D=$(dirname "$(grep -l "^$CHIP" /sys/class/hwmon/hwmon*/name)")
GPU=$(for h in /sys/class/hwmon/hwmon*; do [ "$(cat $h/name)" = amdgpu ] && echo $h; done | head -1)
JUNCTION=$(grep -l junction $GPU/temp*_label | sed 's/_label/_input/')

MIN_RPM=900        # below this a blower is close to stalling
WOBBLE_PCT=15      # a steady fan varies less than this within one step
SETTLE=8           # seconds to let the speed settle after a change
SAMPLE=12          # seconds of readings per step
MARGIN=6           # added to the lowest steady step
STEPS="110 106 102 98 95 92 89 86 83 80 77 74 71 68 65"

restore() {
  echo 255 > $D/pwm$PWM_N 2>/dev/null || true
  systemctl start mi50-fan
  echo
  echo "mi50-fan is back in control."
}
trap restore EXIT

echo "Fan header pwm$PWM_N on $CHIP; current minimum is $CURRENT_MIN."
echo "Pausing mi50-fan for the test (about 5 minutes)..."
systemctl stop mi50-fan
echo 1 > $D/pwm${PWM_N}_enable
echo 150 > $D/pwm$PWM_N
sleep 6

printf "\n  %-4s %-9s %-9s %-7s %s\n" pwm "slowest" "fastest" wobble "junction"
lowest_ok=""
for p in $STEPS; do
  echo $p > $D/pwm$PWM_N
  sleep $SETTLE
  lo=999999; hi=0
  for _ in $(seq $SAMPLE); do
    r=$(cat $D/fan${PWM_N}_input)
    [ "$r" -lt "$lo" ] && lo=$r
    [ "$r" -gt "$hi" ] && hi=$r
    sleep 1
  done
  j=$(( $(cat $JUNCTION) / 1000 ))
  wobble=$(( hi > 0 ? (hi - lo) * 100 / hi : 100 ))
  verdict="steady"
  if [ "$lo" -lt "$MIN_RPM" ]; then verdict="too slow"; elif [ "$wobble" -gt "$WOBBLE_PCT" ]; then verdict="unsteady"; fi
  printf "  %-4s %-9s %-9s %-7s %sC  %s\n" $p "$lo rpm" "$hi rpm" "$wobble%" $j "$verdict"
  if [ "$j" -ge 55 ]; then echo "  GPU reached ${j}C; stopping here to be safe."; break; fi
  [ "$verdict" != steady ] && break
  lowest_ok=$p
done

echo
if [ -z "$lowest_ok" ]; then
  echo "No step below the start was steady; keeping min_pwm $CURRENT_MIN."
  exit 0
fi
recommended=$(( lowest_ok + MARGIN ))
if [ "$recommended" -ge "$CURRENT_MIN" ]; then
  echo "Lowest steady step was $lowest_ok, so $recommended with margin: no quieter than the current $CURRENT_MIN."
  exit 0
fi
echo "Lowest steady step: pwm $lowest_ok. Recommended minimum with a $MARGIN-step margin: $recommended (now $CURRENT_MIN)."
read -r -p "Save min_pwm $recommended to $CONF? [y/N] " answer </dev/tty
if [[ "$answer" =~ ^[Yy] ]]; then
  cp $CONF $CONF.bak-$(date +%Y%m%d-%H%M%S)
  python3 - "$CONF" "$recommended" <<'PY'
import json, sys
path, value = sys.argv[1], int(sys.argv[2])
conf = json.load(open(path))
conf["min_pwm"] = value
json.dump(conf, open(path, "w"), indent=2)
PY
  echo "Saved (backup beside it). mi50-fan picks it up when it restarts in a moment."
else
  echo "Not saved; min_pwm stays $CURRENT_MIN."
fi
