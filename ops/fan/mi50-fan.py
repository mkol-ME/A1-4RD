#!/usr/bin/env python3
"""Drive one motherboard fan header from the MI50's temperatures.

Config: /etc/mi50-fan.conf (JSON), written by install-fan.sh.
Fails safe: any sensor read error -> full speed. On exit -> hand the header back
to the BIOS's own curve (pwm_enable 5), which is what it ran on before.
"""
import collections, glob, json, os, signal, sys, time

CONF = json.load(open("/etc/mi50-fan.conf"))
PCI = CONF.get("gpu_pci", "0000:03:00.0")


def hwmon_by_name(prefix):
    for d in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        try:
            if open(f"{d}/name").read().strip().startswith(prefix):
                yield d
        except OSError:
            pass


def find_paths():
    chip = next(hwmon_by_name(CONF["chip"]))
    gpu = None
    for d in hwmon_by_name("amdgpu"):
        if os.path.realpath(f"{d}/device").endswith(PCI):
            gpu = d
    if gpu is None:
        raise RuntimeError(f"no amdgpu hwmon for {PCI}")
    temps = {}
    for lab in glob.glob(f"{gpu}/temp*_label"):
        temps[open(lab).read().strip()] = lab.replace("_label", "_input")
    return chip, temps


def read(path):
    with open(path) as f:
        return int(f.read().strip())


def write(path, value):
    with open(path, "w") as f:
        f.write(str(value))


def curve(t, lo, hi, pmin, pmax):
    if t <= lo:
        return pmin
    if t >= hi:
        return pmax
    return round(pmin + (pmax - pmin) * (t - lo) / (hi - lo))


def main():
    pwm_n = CONF["pwm"]
    pmin, pmax = CONF["min_pwm"], CONF.get("max_pwm", 255)
    chip, temps = find_paths()
    pwm, enable, fan = f"{chip}/pwm{pwm_n}", f"{chip}/pwm{pwm_n}_enable", f"{chip}/fan{pwm_n}_input"

    def restore(*_):
        try:
            write(pwm, pmax)
            write(enable, CONF.get("restore_enable", 5))
        finally:
            print("mi50-fan: exiting, header handed back to BIOS control", flush=True)
            sys.exit(0)

    signal.signal(signal.SIGTERM, restore)
    signal.signal(signal.SIGINT, restore)

    write(enable, 1)
    current, last_log = pmax, 0
    # A stalled fan on a passively cooled card. The floor was lowered from 110 to
    # 98 after find-floor.sh (2026-09-17), and the step below the one it kept
    # stopped the fan outright, so the floor is now near stall. Nothing used to
    # notice a stopped fan until the card heated enough to raise the curve.
    stall_rpm, stalled_reads = CONF.get("stall_rpm", 300), 0
    # A reply heats the junction 35->55C inside five seconds and it falls just as
    # fast. Steering off the raw reading surged the fan on every sentence, so the
    # curve follows a short rolling average; only a genuinely hot junction
    # (panic_junction) bypasses it.
    window = collections.deque(maxlen=CONF.get("smooth_samples", 8))
    write(pwm, current)
    print(f"mi50-fan: controlling {pwm} from {sorted(temps)}; min={pmin} "
          f"junction {CONF['junction_lo']}-{CONF['junction_hi']}C mem {CONF['mem_lo']}-{CONF['mem_hi']}C", flush=True)

    while True:
        try:
            j = read(temps["junction"]) / 1000
            m = read(temps["mem"]) / 1000
            e = read(temps["edge"]) / 1000
            window.append((j, m))
            js = j if j >= CONF.get("panic_junction", 80) else sum(x for x, _ in window) / len(window)
            ms = sum(y for _, y in window) / len(window)
            target = max(curve(js, CONF["junction_lo"], CONF["junction_hi"], pmin, pmax),
                         curve(ms, CONF["mem_lo"], CONF["mem_hi"], pmin, pmax))
            if target > current:
                current = target                       # heat: respond at once
            elif target < current - CONF.get("hysteresis_pwm", 6):
                current = max(target, current - CONF.get("step_down", 6))   # cool: ease off
        except Exception as exc:                        # can't see the card -> full blast
            print(f"mi50-fan: sensor error {exc!r}; forcing full speed", flush=True)
            current, j, m, e = pmax, -1, -1, -1
            try:
                chip, temps = find_paths()
            except Exception:
                pass
        try:
            if read(enable) != 1:
                write(enable, 1)
            if read(pwm) != current:
                write(pwm, current)
        except (OSError, ValueError) as exc:
            print(f"mi50-fan: write error {exc!r}", flush=True)
        try:
            spinning = read(fan)
        except (OSError, ValueError):
            spinning = None
        # Two slow readings in a row, not one: the tachometer reads 0 for a moment
        # whenever the speed changes sharply.
        stalled_reads = stalled_reads + 1 if spinning is not None and spinning < stall_rpm else 0
        if stalled_reads >= 2:
            print(f"mi50-fan: fan reads {spinning} rpm at pwm {current}; kicking it to full speed "
                  f"and raising this run's floor from {pmin} to {min(pmax, pmin + 8)}", flush=True)
            try:
                write(pwm, pmax)
                time.sleep(3)
            except OSError:
                pass
            pmin = min(pmax, pmin + 8)
            current, stalled_reads = pmax, 0
            continue
        now = time.time()
        if now - last_log >= CONF.get("log_every", 300):
            try:
                rpm = read(fan)
            except (OSError, ValueError):
                rpm = -1
            print(f"mi50-fan: edge {e:.0f}C junction {j:.0f}C mem {m:.0f}C -> pwm {current} ({rpm} rpm)", flush=True)
            last_log = now
        time.sleep(CONF.get("interval", 2))


if __name__ == "__main__":
    main()
