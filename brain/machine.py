"""How the server Alfred runs on is doing: temperatures, fan, power, memory, RAID.

Everything here is readable without root — hwmon, the amdgpu sysfs files,
/proc/mdstat, nvidia-smi — so the voice server can answer "how hot is the
GPU" or "is the RAID healthy" from the machine it is running on. Nothing is
written, and nothing controls the fan: that stays with mi50-fan.service.

    python3 brain/machine.py     # the report the answerer sees
"""

import calendar
import glob
import json
import os
import re
import shutil
import subprocess
import time

import prompts

MI50_PCI = os.environ.get("ALFRED_MI50_PCI", "0000:03:00.0")
FAN_CHIP = os.environ.get("ALFRED_FAN_CHIP", "nct6797")
FAN_HEADER = int(os.environ.get("ALFRED_FAN_HEADER", "7"))
FAN_START_C = 60          # mi50-fan's junction_lo: below this the fan sits at its floor


def _read(path: str, scale: float = 1.0):
    try:
        with open(path) as handle:
            return float(handle.read().strip()) / scale
    except (OSError, ValueError):
        return None


def _hwmon(prefix: str, pci: str | None = None) -> str | None:
    for directory in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        try:
            name = open(f"{directory}/name").read().strip()
        except OSError:
            continue
        if not name.startswith(prefix):
            continue
        if pci and not os.path.realpath(f"{directory}/device").endswith(pci):
            continue
        return directory
    return None


def _labelled(directory: str | None, kind: str = "temp") -> dict:
    readings = {}
    for label in glob.glob(f"{directory}/{kind}*_label") if directory else []:
        try:
            name = open(label).read().strip()
        except OSError:
            continue
        value = _read(label.replace("_label", "_input"), 1000)
        if value is not None:
            readings[name] = value
    return readings


def mi50() -> dict:
    hwmon = _hwmon("amdgpu", MI50_PCI)
    device = f"/sys/bus/pci/devices/{MI50_PCI}"
    temps = _labelled(hwmon)
    power = _read(f"{hwmon}/power1_average", 1_000_000) if hwmon else None
    if power is None and hwmon:
        power = _read(f"{hwmon}/power1_input", 1_000_000)
    return {
        "edge": temps.get("edge"), "junction": temps.get("junction"), "mem": temps.get("mem"),
        "power_w": power, "power_cap_w": _read(f"{hwmon}/power1_cap", 1_000_000) if hwmon else None,
        "busy_pct": _read(f"{device}/gpu_busy_percent"),
        "vram_used_gb": _read(f"{device}/mem_info_vram_used", 1024 ** 3),
        "vram_total_gb": _read(f"{device}/mem_info_vram_total", 1024 ** 3),
        "gtt_used_gb": _read(f"{device}/mem_info_gtt_used", 1024 ** 3),
    }


def gtx1060() -> dict | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5).stdout.strip()
        temp, power, busy, used, total = [part.strip() for part in out.splitlines()[0].split(",")]
        return {"temp": float(temp), "power_w": float(power), "busy_pct": float(busy),
                "vram_used_gb": float(used) / 1024, "vram_total_gb": float(total) / 1024}
    except Exception:
        return None


def fan() -> dict:
    chip = _hwmon(FAN_CHIP)
    pwm = _read(f"{chip}/pwm{FAN_HEADER}") if chip else None
    try:
        service = subprocess.run(["systemctl", "is-active", "mi50-fan"], capture_output=True,
                                 text=True, timeout=5).stdout.strip()
    except Exception:
        service = "unknown"
    return {"rpm": _read(f"{chip}/fan{FAN_HEADER}_input") if chip else None,
            "pwm_pct": round(pwm / 255 * 100) if pwm is not None else None, "service": service}


def cpu() -> dict:
    temps = _labelled(_hwmon("coretemp"))
    load = os.getloadavg()
    return {"package": temps.get("Package id 0"), "load": load[0], "cores": os.cpu_count()}


def nvme() -> float | None:
    return _labelled(_hwmon("nvme")).get("Composite")


def raid() -> list[str]:
    """'md0 [UUU] healthy' per array; a missing disk shows as '_' in the brackets."""
    arrays = []
    try:
        lines = open("/proc/mdstat").read().splitlines()
    except OSError:
        return arrays
    for number, line in enumerate(lines):
        if line.startswith("md") and ":" in line:
            name = line.split()[0]
            state = next((part for part in lines[number + 1].split() if part.startswith("[") and "U" in part), "")
            if not state:
                continue
            syncing = any(word in lines[number + 2] for word in ("recovery", "resync", "check")) \
                if number + 2 < len(lines) else False
            health = "healthy" if "_" not in state else "DEGRADED"
            arrays.append(f"{name} {state} {health}{', checking' if syncing else ''}")
    return arrays


ALERTS = os.environ.get("ALFRED_SERVER_ALERTS", "/var/lib/a1-4rd/alerts.jsonl")
ALERT_DAYS = 30


def alerts(now: float | None = None) -> list[str] | None:
    """Disk and RAID warnings from the last month, newest first; None if nothing records them.

    mdadm and smartd write one JSON line per problem to ALERTS (see the server's
    alert handler). Test messages are left out.
    """
    try:
        lines = open(ALERTS, encoding="utf-8").read().splitlines()
    except OSError:
        return None
    since = (now or time.time()) - ALERT_DAYS * 86400
    found = []
    for line in lines:
        try:
            entry = json.loads(line)
            when = calendar.timegm(time.strptime(entry["time"], "%Y-%m-%dT%H:%M:%SZ"))
        except (ValueError, KeyError, TypeError):
            continue
        if entry.get("test") or when < since:
            continue
        found.append(f"{time.strftime('%b %d', time.gmtime(when))}: {entry.get('message', entry.get('event'))}")
    return found[::-1]


def disks() -> list[str]:
    report = []
    for label, path in (("system", "/"), ("storage array", "/srv/storage")):
        try:
            usage = shutil.disk_usage(path)
            report.append(f"{label} {usage.used / usage.total * 100:.0f}% full "
                          f"({usage.free / 1024 ** 3:.0f} GB free)")
        except OSError:
            pass
    return report


def uptime() -> str:
    seconds = _read("/proc/uptime") or 0
    seconds = float(open("/proc/uptime").read().split()[0]) if os.path.exists("/proc/uptime") else seconds
    days, rest = divmod(int(seconds), 86400)
    hours = rest // 3600
    return f"{days} day{'s' if days != 1 else ''} {hours} h" if days else f"{hours} h {rest % 3600 // 60} min"


def _run(*command: str) -> str:
    try:
        return subprocess.run(list(command), capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return ""


_inventory: list[str] = []


def inventory() -> list[str]:
    """What the machine is made of, and what each part is for. Read once; it does not change."""
    if _inventory:
        return _inventory
    def dmi(field):
        try:
            return open(f"/sys/class/dmi/id/{field}").read().strip()
        except OSError:
            return ""
    lines = []
    board = " ".join(part for part in (dmi("board_vendor").replace(" Co., Ltd.", ""), dmi("board_name")) if part)
    if board:
        lines.append(f"- Motherboard: {board}, BIOS {dmi('bios_version') or 'unknown'}")
    model = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), "unknown CPU")
    memory = next((int(l.split()[1]) for l in open("/proc/meminfo") if l.startswith("MemTotal")), 0) / 1024 ** 2
    # MemTotal leaves out what firmware reserves: 48 GB installed reads as 47.
    installed = -(-memory // 8) * 8 if memory > 6 else memory
    lines.append(f"- CPU: {model}, {os.cpu_count()} threads; {installed:.0f} GB RAM")
    gpus = [l.split(": ", 1)[1] for l in _run("lspci").splitlines()
            if any(kind in l for kind in ("VGA compatible", "Display controller", "3D controller"))]
    vbios = ""
    try:
        vbios = open(f"/sys/bus/pci/devices/{MI50_PCI}/vbios_version").read().strip()
    except OSError:
        pass
    for gpu in gpus:
        if "MI50" in gpu or "Vega 20" in gpu:
            model_name = ""
            try:
                import alfred
                model_name = f" ({alfred.DEFAULT_MODEL})"
            except Exception:
                pass
            ollama = _run("ollama", "--version").strip().replace("ollama version is ", "")
            lines.append(f"- AMD Radeon Instinct MI50, 32 GB HBM2, passively cooled with a server fan on the "
                         f"motherboard: runs your language model{model_name} through Ollama {ollama} on Vulkan"
                         + (f"; VBIOS {vbios} (stock, reflashed from a cross-flashed Apple ROM)" if vbios else ""))
        elif "GTX 1060" in gpu or "GP106" in gpu:
            driver = _run("nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader").strip()
            lines.append(f"- NVIDIA GeForce GTX 1060 6 GB: runs Whisper, your speech recognition"
                         + (f"; driver {driver}" if driver else ""))
        else:
            lines.append(f"- GPU: {gpu}")
    members = {}
    try:
        for line in open("/proc/mdstat"):
            if line.startswith("md") and ":" in line:
                name = line.split()[0]
                for part in line.split()[4:]:
                    members[re.sub(r"\d*\[\d+\]$", "", part)] = name
    except OSError:
        pass
    try:
        devices = json.loads(_run("lsblk", "-J", "-d", "-o", "NAME,MODEL,SIZE,ROTA,TRAN")).get("blockdevices", [])
    except ValueError:
        devices = []
    for device in devices:
        kind = "hard drive" if device.get("rota") in (True, "1") else "SSD"
        role = (f"in RAID 5 array {members[device['name']]} (holds your memory database)"
                if device["name"] in members else
                "system drive (Ubuntu, models)" if device["name"].startswith("nvme") else "spare storage")
        lines.append(f"- {device.get('model') or device['name']} {device.get('size')} {kind}: {role}")
    release = next((l.split("=", 1)[1].strip().strip('"') for l in open("/etc/os-release")
                    if l.startswith("PRETTY_NAME")), "Linux")
    lines.append(f"- {release}, kernel {os.uname().release}; reached over the LAN and Tailscale")
    _inventory.extend(lines)
    return _inventory


def _c(value) -> str:
    return f"{value:.0f}°C" if value is not None else "unknown"


def report() -> str:
    gpu, other, fans, processor = mi50(), gtx1060(), fan(), cpu()
    lines = [f"Readings from the server you run on, taken {time.strftime('%H:%M')}. Current and exact; "
             f"say the numbers plainly. The fan speeds up only above {FAN_START_C}°C junction and holds its "
             f"floor below that. They are taken while you are answering, so the MI50 is warmed by this very "
             f"reply: asked about heat or noise, say that at rest it sits near 30°C."]
    lines.append(f"- MI50 (runs the language model): junction {_c(gpu['junction'])}, edge {_c(gpu['edge'])}, "
                 f"memory {_c(gpu['mem'])}; "
                 + (f"{gpu['power_w']:.0f} W of {gpu['power_cap_w']:.0f} W; " if gpu["power_w"] is not None and gpu["power_cap_w"] else "")
                 + (f"{gpu['busy_pct']:.0f}% busy; " if gpu["busy_pct"] is not None else "")
                 + (f"VRAM {gpu['vram_used_gb']:.1f} of {gpu['vram_total_gb']:.1f} GB" if gpu["vram_used_gb"] is not None else ""))
    if gpu.get("gtt_used_gb") and gpu["gtt_used_gb"] > 1.5:
        lines.append(f"  WARNING: {gpu['gtt_used_gb']:.1f} GB has spilled into system RAM; replies will be slow.")
    if other:
        lines.append(f"- GTX 1060 (speech recognition): {_c(other['temp'])}, {other['power_w']:.0f} W, "
                     f"{other['busy_pct']:.0f}% busy, VRAM {other['vram_used_gb']:.1f} of {other['vram_total_gb']:.1f} GB")
    lines.append(f"- MI50 fan: {fans['rpm']:.0f} rpm, {fans['pwm_pct']}% power, control service {fans['service']}"
                 if fans["rpm"] is not None else f"- MI50 fan: no reading, control service {fans['service']}")
    lines.append(f"- CPU: {_c(processor['package'])}, load {processor['load']:.2f} on {processor['cores']} threads; "
                 f"NVMe {_c(nvme())}; up {uptime()}")
    arrays = raid()
    if arrays:
        lines.append("- RAID: " + "; ".join(arrays))
    storage = disks()
    if storage:
        lines.append("- Disks: " + "; ".join(storage))
    warnings = alerts()
    if warnings:
        lines.append(f"- Disk and RAID alerts in the last {ALERT_DAYS} days: " + "; ".join(warnings[:5]))
    elif warnings is not None:
        lines.append(f"- Disk health monitor: no disk or RAID alerts in the last {ALERT_DAYS} days")
    # "the server you run on" came back as "You're running an i7-8700, sir":
    # he mirrored the second person onto the owner. Say whose hardware it is.
    lines.append(f"Hardware of the server that is your brain. It is YOUR hardware, not {prompts.OWNER}'s: say "
                 f"\"I run on…\" or \"my GPU is…\", never \"you're running\". {prompts.OWNER}'s laptop is only your "
                 "microphone and speaker for now; a Raspberry Pi in your printed body will be later:")
    lines.extend(inventory())
    return "\n".join(lines)


def lookup() -> dict:
    return {"ok": True, "found": 1, "report": report()}


if __name__ == "__main__":
    print(report())
