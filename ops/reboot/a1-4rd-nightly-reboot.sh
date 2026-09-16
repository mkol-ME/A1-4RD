#!/bin/bash
# Reboot the box at ~3am Eastern if it has been up long enough and nothing is happening.
# Opt out any time:  sudo touch /etc/a1-4rd-no-auto-reboot
MIN_UPTIME_H=60          # timer fires nightly; 60h floor => a reboot every third night
GIVE_UP_HOUR=5           # keep retrying every 15 min until 5am Eastern, then skip the night
log() { echo "nightly-reboot: $*"; }

busy_reason() {
  [ -e /etc/a1-4rd-no-auto-reboot ] && { echo "opt-out file present"; return; }
  grep -qE "resync|recover|check|reshape" /proc/mdstat && { echo "RAID resync/check in progress"; return; }
  pgrep -f "ollama pull" >/dev/null && { echo "model download running"; return; }
  fuser /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock >/dev/null 2>&1 && { echo "package manager running"; return; }
  now=$(date +%s)
  while read -r _ tty _; do
    [ -e "/dev/$tty" ] || continue
    idle=$(( now - $(stat -c %X "/dev/$tty") ))
    [ "$idle" -lt 1800 ] && { echo "someone active on $tty (idle ${idle}s)"; return; }
  done < <(who)
  load5=$(awk '{print $2}' /proc/loadavg)
  awk -v l="$load5" 'BEGIN{exit !(l>2.0)}' && { echo "CPU load $load5"; return; }
  amd=0; nv=0
  for _ in $(seq 12); do
    a=$(cat /sys/bus/pci/devices/0000:03:00.0/gpu_busy_percent 2>/dev/null || echo 0)
    n=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 || echo 0)
    amd=$(( amd + a )); nv=$(( nv + ${n:-0} )); sleep 5
  done
  [ $(( amd / 12 )) -gt 10 ] && { echo "MI50 busy $(( amd / 12 ))%"; return; }
  [ $(( nv / 12 )) -gt 10 ] && { echo "GTX 1060 busy $(( nv / 12 ))%"; return; }
}

up_h=$(( $(awk '{print int($1)}' /proc/uptime) / 3600 ))
if [ "$up_h" -lt "$MIN_UPTIME_H" ]; then log "up ${up_h}h (< ${MIN_UPTIME_H}h), not due"; exit 0; fi

while :; do
  reason=$(busy_reason)
  if [ -z "$reason" ]; then
    log "up ${up_h}h and idle, rebooting"
    sync; systemctl reboot; exit 0
  fi
  hour=$(TZ=America/New_York date +%-H)
  if [ "$hour" -ge "$GIVE_UP_HOUR" ]; then log "still busy ($reason) at ${hour}:00 ET, skipping tonight"; exit 0; fi
  log "busy ($reason), retrying in 15 min"
  sleep 900
done
