#!/bin/bash
# Run once, from the project root on the box:  sudo bash ops/fan/install-fan.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "== 1/5 loading the fan-header driver now and on every boot"
modprobe nct6775
echo nct6775 > /etc/modules-load.d/nct6775.conf

CHIP_DIR=""
for d in /sys/class/hwmon/hwmon*; do
  case "$(cat $d/name)" in nct67*) CHIP_DIR=$d; CHIP=$(cat $d/name);; esac
done
[ -n "$CHIP_DIR" ] || { echo "no nct67xx chip found"; exit 1; }
echo "   chip: $CHIP at $CHIP_DIR"

rpm() { cat "$CHIP_DIR/fan$1_input" 2>/dev/null || echo 0; }
systemctl stop mi50-fan 2>/dev/null || true

echo "== 2/5 finding the server fan's header"
CANDS=$(for f in "$CHIP_DIR"/fan[0-9]_input; do n=${f##*fan}; n=${n%_input}; r=$(cat $f); [ "$r" -gt 0 ] && [ -e "$CHIP_DIR/pwm$n" ] && echo "$r $n"; done | sort -rn | awk '{print $2}')
echo "   headers with a spinning fan: $(for n in $CANDS; do echo -n "pwm$n=$(rpm $n)rpm  "; done)"
CHOSEN=""
for n in $CANDS; do
  E=$(cat $CHIP_DIR/pwm${n}_enable); P=$(cat $CHIP_DIR/pwm$n)
  before=$(rpm $n)
  echo; echo "   testing header $n (now $before rpm): slowing it down for ~10 seconds..."
  echo 1 > $CHIP_DIR/pwm${n}_enable; echo 60 > $CHIP_DIR/pwm$n
  sleep 8; after=$(rpm $n)
  echo "   header $n: $before rpm -> $after rpm"
  read -r -p "   Did the LOUD server fan on the MI50 just get noticeably quieter? [y/N] " ans </dev/tty
  echo $P > $CHIP_DIR/pwm$n; echo $E > $CHIP_DIR/pwm${n}_enable
  if [[ "$ans" =~ ^[Yy] ]]; then CHOSEN=$n; RESTORE_ENABLE=$E; break; fi
  sleep 3
done
[ -n "$CHOSEN" ] || { echo "no header confirmed; nothing installed (driver persistence kept)."; exit 1; }
echo "   -> MI50 fan is on header $CHOSEN"

echo; echo "== 3/5 measuring the fan's slowest reliable speed (~1 minute, it will get loud first)"
echo 1 > $CHIP_DIR/pwm${CHOSEN}_enable
last_ok=255; printf "   %-5s %s\n" pwm rpm
for p in 255 200 160 128 100 80 64 52 42 34 26 18; do
  echo $p > $CHIP_DIR/pwm$CHOSEN; sleep 6; r=$(rpm $CHOSEN)
  printf "   %-5s %s\n" $p $r
  if [ "$r" -lt 200 ]; then break; fi
  last_ok=$p
done
MIN=$(( last_ok + 10 )); [ $MIN -gt 255 ] && MIN=255
echo 255 > $CHIP_DIR/pwm$CHOSEN
echo "   slowest steady pwm $last_ok -> using floor $MIN"

echo; echo "== 4/5 installing the fan service"
cat > /etc/mi50-fan.conf <<CONF
{
  "chip": "$CHIP",
  "pwm": $CHOSEN,
  "min_pwm": $MIN,
  "max_pwm": 255,
  "restore_enable": $RESTORE_ENABLE,
  "gpu_pci": "0000:03:00.0",
  "junction_lo": 60, "junction_hi": 85,
  "mem_lo": 60, "mem_hi": 85,
  "interval": 2, "step_down": 6, "hysteresis_pwm": 6, "log_every": 300,
  "smooth_samples": 8, "panic_junction": 80
}
CONF
install -m 755 "$HERE/mi50-fan.py" /usr/local/sbin/mi50-fan.py
install -m 644 "$HERE/mi50-fan.service" /etc/systemd/system/mi50-fan.service
systemctl daemon-reload
systemctl enable --now mi50-fan

echo; echo "== 5/5 status"
sleep 8
systemctl --no-pager --lines=5 status mi50-fan || true
echo "   header $CHOSEN now at pwm $(cat $CHIP_DIR/pwm$CHOSEN), $(rpm $CHOSEN) rpm"
echo "DONE"
