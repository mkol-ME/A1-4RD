# Running Alfred

## The client

From the project root on the laptop, in PowerShell. The client starts any server services that are not
running and opens the SSH tunnels itself ([reaching the server](SSH.md)).

```powershell
.venv-tts\Scripts\python.exe client\listen.py            # speak: say "Alfred, ..."
.venv-tts\Scripts\python.exe client\listen.py --open     # no wake word
.venv-tts\Scripts\python.exe client\talk.py              # type, and hear him answer
python client\chat.py                                    # type, text only (standard library)
```

Each spoken turn prints what was heard, how long transcription took, and the longest pause left inside the
sentence: the data for tuning when a turn is considered over. **Ctrl+C** quits. Everything said is
remembered, exactly as in normal use.

Terminal chat directly on the server, with no audio:

```bash
cd ~/a1-4rd && .venv-rvc/bin/python brain/alfred.py
```

## Services

| Service | What it runs | Started by |
|---|---|---|
| Ollama | `gemma4:26b-a4b-it-q8_0` on the MI50 | systemd (`ollama`) |
| voice server | `brain/voice_server.py` | systemd (`alfred-voice`) |
| Whisper | `brain/whisper_server.py` | systemd (`alfred-whisper`) |
| SearXNG | metasearch | systemd (`alfred-searx`) |
| media service | `brain/media_server.py`, YouTube search and audio | systemd (`alfred-media`) |

All of them listen on localhost only; the laptop reaches them through SSH port forwarding.
`client/listen.py` still starts any that are not running. Install the units with
`sudo bash ops/services/install.sh`.

## Installed system pieces ([`ops/`](../ops))

| Unit | What it does |
|---|---|
| `mi50-fan.service` | fan speed from the MI50's junction and memory temperature; full speed if the sensor is lost |
| `a1-4rd-nightly-reboot.timer` | 3 a.m.: reboots only if up ≥ 60 h and idle (no RAID check, downloads, updates, SSH activity or GPU load). Opt out: `sudo touch /etc/a1-4rd-no-auto-reboot` |
| `alfred-voice`, `alfred-whisper`, `alfred-searx` | Alfred's services, up at boot and restarted if they crash ([`ops/services`](../ops/services)) |
| `01-keys-only.conf`, `tailscaled` | SSH by key only; reachable from any network through Tailscale, no open router port ([`ops/remote-access`](../ops/remote-access)) |
| `alfred-ollama-warm.service` | loads Alfred's model at boot so the first reply is not a 20 s load |
| `ollama.service.d/override.conf` | see below |

## Ollama settings

Why each setting in [`ops/ollama/override.conf`](../ops/ollama/override.conf) is there:

| Setting | Reason |
|---|---|
| `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1`, `RADV_PERFTEST=nogttspill` | the MI50 exposes only 16 GB to the CPU; without these half the model silently lands in system RAM (4 tok/s instead of 40) |
| `OLLAMA_NUM_PARALLEL=2` | the tool decider and Alfred's persona each keep their own cached prompt |
| `LLAMA_ARG_SWA_FULL=1`, `LLAMA_ARG_CTX_CHECKPOINTS=0`, `LLAMA_ARG_CACHE_RAM=0` | stop llama.cpp copying ~100 MB of cache off the card every request (−0.47 s per turn) |
| `OLLAMA_MAX_LOADED_MODELS=2` | Alfred + the embedder; anything extra evicts instead of spilling into RAM |
| `OLLAMA_KEEP_ALIVE=-1` | the model never unloads |

VRAM is ~31 of 32.75 GB in use. Loading another model onto the MI50 alongside Alfred will slow him down.
The board boots in legacy (CSM) mode; do not disable CSM.

## Useful checks

```bash
ollama ps                                                    # model loaded, 100% GPU
cat /sys/bus/pci/devices/0000:03:00.0/mem_info_gtt_used      # should stay under ~1 GB
sensors amdgpu-pci-0300                                      # MI50 temperatures and power
journalctl -u mi50-fan -n 5                                  # fan curve decisions
systemctl list-timers a1-4rd-nightly-reboot.timer
```

## What is not in git

Large assets live at the project root on the server: the virtual environments (`.venv-rvc`,
`.venv-whisper`), `voice-audition-distilled/` (his current voice), `tts-models/`, `rvc-model/`, and the
training data under `voice-distill/` and `piper-training/`.
