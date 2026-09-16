# A1-4RD — "Alfred"

A 3D-printed desk companion with a moving jaw and a voice, in the spirit of Alfred Pennyworth from
*Batman: The Animated Series*: dry, warm, terse, and genuinely useful. Not a smart speaker.

Everything runs locally. A laptop (later a Raspberry Pi inside the printed body) is the face: microphone,
speaker, wake word. A headless Ubuntu box on the LAN is the brain: speech recognition, memory, web lookup,
the language model and his voice. Nothing is sent to a hosted service.

> **The character is the project. Everything else is plumbing.**

## What I built, and what I learned

I built a voice assistant with a fixed personality that runs entirely on my own hardware: speech detection
and wake word on a laptop, and Whisper, a 26-billion-parameter language model, long-term memory, web and
weather lookup and a custom synthesized voice on a home server. That server runs on a secondhand datacenter
GPU I had to reflash and coax into a consumer motherboard. Through measurement rather than guesswork, I got
a spoken reply's first sound down to about 1.15 seconds, and a web-searched answer from 7.1 to 3.5 seconds.
The biggest lesson was that intuition is unreliable with language models. Adding rules to the prompt made
the character worse three separate times. My first test suite passed while the real failures went
undetected, because its questions had leaked into the training examples. Two confident theories about why
he rambled both turned out wrong. So I built a held-out evaluation that checks its own contamination, and
changed things only when a number moved. I also learned to put boundaries in code rather than instructions:
anything that reaches the prompt will eventually be said out loud, so access to memory has to be enforced in
the database query itself.

---

## Contents

- [How a spoken turn works](#how-a-spoken-turn-works)
- [Hardware](#hardware)
- [Repository layout](#repository-layout)
- [Talking to Alfred](#talking-to-alfred)
- [The server](#the-server)
- [Performance](#performance)
- [Testing](#testing)
- [Status and roadmap](#status-and-roadmap)
- [Further reading](#further-reading)

---

## How a spoken turn works

```text
 LAPTOP (client/)                               SERVER (brain/, over an SSH tunnel)
 ─────────────────                              ───────────────────────────────────────────────
 microphone, 16 kHz
   → speech detection against the room's
     measured noise floor
   → at 0.20 s of silence, send audio ────────→ Whisper small.en on the GTX 1060        (:5052)
   → at 0.40 s, end the turn — or wait up to
     1.0 s if the words so far trail off
   → wake word / attention window
   → text ────────────────────────────────────→ voice server                            (:5051)
                                                  → tool gate: does this need a lookup?
                                                  → decider: search memory / search web
                                                    (SearXNG :8888, Wikipedia) / remember
                                                    weather goes to Open-Meteo instead
                                                  → gemma4 26B on the MI50 via Ollama   (:11434)
                                                  → cut the stream into whole sentences
                                                  → Alfred's distilled Piper voice (CPU)
 speaker (WASAPI) ←──── one WAV per sentence ─── ← streamed as NDJSON
```

The pieces are deliberately separable:

| Layer | Files | Decides |
|---|---|---|
| **Character** | `persona/alfred.md`, `persona/examples.md` | how he behaves |
| **Knowledge** | `brain/memory.py`, `brain/memory_tools.py`, `brain/web.py`, `brain/weather.py` | what evidence he sees |
| **Transport** | `brain/voice_server.py`, `brain/whisper_server.py`, SSH | how text and audio move |
| **Embodiment** | `client/listen.py`, `client/talk.py`, later the servos | how he is present in the room |

A better voice cannot fix a bad answer, and a longer prompt cannot replace memory, so each layer is
debugged on its own.

---

## Hardware

**Server** (headless Ubuntu 24.04, `ssh a1-4rd`, see [docs/SSH.md](docs/SSH.md))

| Part | Role |
|---|---|
| i7-8700 · 48 GB DDR4 · MSI MPG Z390 Gaming Plus | host |
| **AMD Radeon Instinct MI50 32 GB** | the language model (Ollama, Vulkan backend) |
| **NVIDIA GTX 1060 6 GB** | Whisper |
| 500 GB NVMe · 3×2 TB RAID 5 (`/srv/storage`) · 1.5 TB (`/srv/extra`) | OS and models · Alfred's memory database · spare |

MI50 notes, all handled already: it needed its stock VBIOS reflashed, *Above 4G Decoding* in the BIOS, and
`pci=realloc` on the kernel command line. It is passively cooled, so a server fan on motherboard header 7 is
driven from the card's temperature by [`ops/fan`](ops/fan). The board boots in legacy (CSM) mode — do not
disable CSM.

**Client:** any Windows laptop with a microphone. Later: a Raspberry Pi, servo jaw, neck servo and a printed
enclosure — see [`hardware/`](hardware).

---

## Repository layout

```text
A1-4RD/
├── brain/                    runs on the server
│   ├── alfred.py             model choice, prompt assembly, streaming; also a terminal chat client
│   ├── memory.py             SQLite memory: recent conversation, facts, semantic search
│   ├── memory_tools.py       the tool decider and its tools (memory, web, facts)
│   ├── web.py                Wikipedia + SearXNG lookup, run concurrently
│   ├── weather.py            live forecast from Open-Meteo, not search snippets
│   ├── media.py              "play…" / "find videos of…" requests and spoken titles
│   ├── media_server.py       YouTube search and audio stream (own venv: yt-dlp, PyAV)
│   ├── voice_server.py       one spoken turn end to end, streamed sentence by sentence
│   ├── whisper_server.py     resident Whisper, so no model load per utterance
│   ├── whisper_transcribe.py one-off file transcription
│   ├── character_eval.py     held-out character test — the one to trust
│   └── routing_eval.py       does each question reach the right lookup (web, memory, none)
├── persona/
│   ├── alfred.md             who he is
│   └── examples.md           how he talks, as real conversation turns
├── client/                   runs on the laptop
│   ├── listen.py             speak to him: wake word, attention window, early transcription
│   ├── talk.py               type to him, hear him answer; also the audio player
│   ├── music.py              plays YouTube audio; pause, stop, volume, ducking under his voice
│   └── launcher/             builds Alfred.exe, a double-click launcher
├── scripts/                  server launch scripts (voice, Whisper, SearXNG)
├── voice-training/           how his voice was made: auditions, RVC, distillation into Piper
├── tests/                    unit tests for memory, tool gate and the listening loop
├── ops/                      server setup, version-controlled
│   ├── fan/                  MI50 fan curve service + interactive installer
│   ├── reboot/               idle-only 3 a.m. reboot every third night
│   ├── ollama/               Ollama settings and boot-time model preload
│   ├── services/             start SearXNG, Whisper and the voice server at boot
│   └── remote-access/        key-only SSH and Tailscale
├── requirements/             pinned environments (client TTS, Whisper, RVC, Qwen-TTS)
├── hardware/                 CAD spec and PCB notes for the body
├── docs/                     SSH access, design notes and project history
└── legacy/                   retired pieces kept for reference (the unused Modelfile)
```

Large assets are **not** in git and live at the project root on the server: the virtual environments
(`.venv-rvc`, `.venv-whisper`), `voice-audition-distilled/` (his current voice), `tts-models/`,
`rvc-model/`, and the training data under `voice-distill/` and `piper-training/`.

---

## Talking to Alfred

From the project root on the laptop, in PowerShell. The client starts any server services that are not
running and opens the SSH tunnels itself.

```powershell
.venv-tts\Scripts\python.exe client\listen.py            # speak: say "Alfred, ..."
.venv-tts\Scripts\python.exe client\listen.py --open     # no wake word
.venv-tts\Scripts\python.exe client\talk.py              # type instead of speaking
```

- Say **"Alfred, …"** to start. He then stays attentive for three minutes without needing his name.
- **"That'll be all"** dismisses him. **Ctrl+C** quits.
- **"Play …"** plays it from YouTube through his speaker; **"find videos of …"** reads out the top results, then
  **"play the second one"** or **"next"**. While music plays, say his name first: **"Alfred, pause / resume / stop /
  louder / quieter"**. The music drops while he talks.
- Each turn prints what was heard, how long transcription took, and the longest pause you left inside the
  sentence — the data for tuning when a turn is considered over.

Everything said is remembered, exactly as in normal use.

Terminal chat directly on the server (no audio):

```bash
ssh a1-4rd "cd ~/a1-4rd && .venv-rvc/bin/python brain/alfred.py"
```

---

## The server

### Services

| Port | Service | Started by |
|---|---|---|
| 11434 | Ollama — `gemma4:26b-a4b-it-q8_0` on the MI50 | systemd (`ollama`) |
| 5051 | voice server (`brain/voice_server.py`) | systemd (`alfred-voice`) |
| 5052 | Whisper (`brain/whisper_server.py`) | systemd (`alfred-whisper`) |
| 8888 | SearXNG metasearch, localhost only | systemd (`alfred-searx`) |
| 5053 | media service (`brain/media_server.py`), YouTube search and audio | systemd (`alfred-media`) |

All bind to `127.0.0.1`; the laptop reaches them through SSH port forwarding, over the LAN or Tailscale.
`client/listen.py` still starts any that are not running. Install the units with
`sudo bash ops/services/install.sh`.

### Installed system pieces ([`ops/`](ops))

| Unit | What it does |
|---|---|
| `mi50-fan.service` | fan speed from MI50 junction/memory temperature; full speed if the sensor is lost |
| `a1-4rd-nightly-reboot.timer` | 3 a.m. Eastern: reboots only if up ≥ 60 h and idle (no RAID check, downloads, updates, SSH activity or GPU load). Opt out: `sudo touch /etc/a1-4rd-no-auto-reboot` |
| `alfred-voice`, `alfred-whisper`, `alfred-searx` | Alfred's services, up at boot and restarted if they crash ([`ops/services`](ops/services)) |
| `01-keys-only.conf`, `tailscaled` | SSH by key only; reachable from any network through Tailscale, no open router port ([`ops/remote-access`](ops/remote-access)) |
| `alfred-ollama-warm.service` | loads Alfred's model at boot so the first reply is not a 20 s load |
| `ollama.service.d/override.conf` | see below |

Why each Ollama setting is there ([`ops/ollama/override.conf`](ops/ollama/override.conf)):

| Setting | Reason |
|---|---|
| `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1`, `RADV_PERFTEST=nogttspill` | the MI50 exposes only 16 GB to the CPU; without these half the model silently lands in system RAM (4 tok/s instead of 40) |
| `OLLAMA_NUM_PARALLEL=2` | the tool decider and Alfred's persona each keep their own cached prompt |
| `LLAMA_ARG_SWA_FULL=1`, `LLAMA_ARG_CTX_CHECKPOINTS=0`, `LLAMA_ARG_CACHE_RAM=0` | stop llama.cpp copying ~100 MB of cache off the card every request (−0.47 s per turn) |
| `OLLAMA_MAX_LOADED_MODELS=2` | Alfred + the embedder; anything extra evicts instead of spilling into RAM |
| `OLLAMA_KEEP_ALIVE=-1` | the model never unloads |

VRAM is ~31 of 32.75 GB in use. Loading another model onto the MI50 alongside Alfred will slow him down.

### Useful checks

```bash
ollama ps                                                    # model loaded, 100% GPU
cat /sys/bus/pci/devices/0000:03:00.0/mem_info_gtt_used      # should stay under ~1 GB
sensors amdgpu-pci-0300                                      # MI50 temperatures and power
journalctl -u mi50-fan -n 5                                  # fan curve decisions
systemctl list-timers a1-4rd-nightly-reboot.timer
```

---

## Performance

Measured 2026-09-16, from the end of speech to Alfred's first sound, with real audio through the whole
pipeline:

| Turn | Before the MI50 work | Now |
|---|---|---|
| Plain conversation ("why do my prints warp") | 1.5 s | **≈ 1.15 s** |
| Needs the tool decider ("what should I have for dinner") | 4.2 s | **≈ 1.6 s** |
| Memory lookup ("what did I tell you about…") | 4.5 s | **≈ 1.9 s** |
| Web search, real answer (holding line at ≈ 1.0 s) | 7.1 s | **≈ 3.5 s** |

**Model choice.** Candidates run on the MI50 with Alfred's real prompt:

| Model | First sentence | Speed | Character eval |
|---|---|---|---|
| **gemma4:26b Q8** (in use) | **0.43 s** | 41 tok/s | **75/78** |
| gemma4:31b | 1.61 s | 15 tok/s | 77/78 |
| qwen3.6:35b-a3b | 1.35 s | 54 tok/s | 75/78 |
| qwen3.8:27b | 5.50 s | 17 tok/s | — |
| qwen3.5:9b (previous) | 1.77 s | 63 tok/s | 67/78 |

The Qwen 3.x models re-read the whole persona on every turn; Gemma reuses the cached prefix, which is most of
the gap. `gemma4:31b` is the alternative if character ever matters more than speed — one line in
`brain/alfred.py`.

---

## Testing

```bash
# character — run after any change to persona/ or the prompt wording (≈1 min)
ssh a1-4rd "cd ~/a1-4rd && .venv-rvc/bin/python brain/character_eval.py --samples 3"

# routing — run after any change to the tool gate or decider wording (≈1 min)
ssh a1-4rd "cd ~/a1-4rd && .venv-rvc/bin/python brain/routing_eval.py"

# memory, tool gate and decider history rules (on the server)
ssh a1-4rd "cd ~/a1-4rd && .venv-rvc/bin/python -m unittest discover -s tests -p 'test_memory.py'"
```

```powershell
# listening loop: segmentation, wake word, early transcription, unfinished sentences (on the laptop)
.venv-tts\Scripts\python.exe -m unittest discover -s tests -p "test_listen.py"
```

`character_eval.py` checks that its own probes are not contaminated by `examples.md` before it scores
anything. The older `/test` battery inside `alfred.py` is contaminated and cannot detect the main failure —
see the design notes.

---

## Status and roadmap

**Done:** persona (phase 1); the full voice pipeline — text, memory, voice, ears (phase 2); MI50 bring-up and
latency work; services that start at boot; remote access over Tailscale; live weather; handling spoken
corrections.

**Next**
- Recognising who is speaking, with separate memory for a housemate (enforced in SQL, never in the prompt)
- Small character faults — through example curation, not more rules

**Later:** Raspberry Pi client, servo jaw and neck, printed enclosure; Tapology, then Spotify.

---

## Further reading

- [docs/DESIGN-NOTES.md](docs/DESIGN-NOTES.md) — how the design got here: what was tried and failed, settled
  decisions, and notes for anyone (or any agent) working on Alfred
- [docs/SSH.md](docs/SSH.md) — reaching the server
- [hardware/](hardware) — the physical build
