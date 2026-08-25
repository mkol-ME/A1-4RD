#!/usr/bin/env python3
"""A1-4RD — Phase 2, Step 1. Terminal only. Stdlib only.

    python3 alfred.py                 # uses DEFAULT_MODEL
    python3 alfred.py llama3.1:8b     # or name one on the command line

Commands:
    /test           run the battery, each case in a fresh context
    /model NAME     switch model without restarting
    /reload         re-read alfred.md
    /reset          clear the conversation, keep the persona
    /quit
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from memory import Memory

SERVER = "http://localhost:11434"   # server's IP if running from the laptop
DEFAULT_MODEL = "qwen3.5:9b"
PERSONA = Path(__file__).with_name("alfred.md")
EXAMPLES = Path(__file__).with_name("examples.md")
MEMORY_DB = Path(os.environ.get("ALFRED_MEMORY_DB", Path(__file__).with_name(".alfred-memory.sqlite3")))

TEMPERATURE = 0.75
MAX_TOKENS = -1         # -1 = uncapped; set a number only as a runaway guard

SHOTS = []

DIM = "\033[2m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"

# Each case is a list of user turns. Multi-turn cases generate the intermediate
# reply for real, so the final turn has something genuine to respond to.
TESTS = []


def load_persona() -> str:
    if not PERSONA.exists():
        sys.exit(f"{RED}Can't find {PERSONA.name} next to this script.{RESET}")
    return PERSONA.read_text(encoding="utf-8").strip()


def load_examples() -> list:
    """Parse examples.md into alternating user/assistant turns."""
    if not EXAMPLES.exists():
        return []
    shots = []
    for raw in EXAMPLES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("M:"):
            shots.append({"role": "user", "content": line[2:].strip()})
        elif line.startswith("A:"):
            shots.append({"role": "assistant", "content": line[2:].strip()})
    return shots


def ask(model, persona, history, memory_context="", echo=True, stats=True) -> str:
    """Stream one reply. Returns the full text. echo=False keeps it off screen."""
    messages = [{"role": "system", "content": persona}]
    if memory_context:
        messages.append({"role": "system", "content": memory_context})
    messages += SHOTS + history
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "think": False,
        "options": {
            "temperature": TEMPERATURE,
            "top_p": 0.85,
            "repeat_penalty": 1.05,
            "num_predict": MAX_TOKENS,
        },
    }
    req = urllib.request.Request(
        f"{SERVER}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    parts, count, first = [], 0, None
    start = time.time()

    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            if not raw.strip():
                continue
            chunk = json.loads(raw)
            if "error" in chunk:
                raise RuntimeError(chunk["error"])
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                if first is None:
                    first = time.time() - start
                if echo:
                    sys.stdout.write(piece)
                    sys.stdout.flush()
                parts.append(piece)
                count += 1
            if chunk.get("done"):
                break

    elapsed = time.time() - start
    if echo:
        print()
        if stats and elapsed > 0 and first is not None:
            print(f"{DIM}{first:.2f}s to first token · {count/elapsed:.0f} tok/s{RESET}")
    return "".join(parts).strip()


def run_tests(model, persona) -> None:
    print(f"\n{DIM}══ {model} ══{RESET}")
    for i, (probe, turns) in enumerate(TESTS, 1):
        print(f"\n{DIM}── {i}/{len(TESTS)} · {probe} ──{RESET}")
        history = []
        try:
            for j, turn in enumerate(turns):
                last = j == len(turns) - 1
                print(f"{CYAN}{turn}{RESET}" if last else f"{DIM}{turn}{RESET}")
                history.append({"role": "user", "content": turn})
                reply = ask(model, persona, history, echo=last, stats=False)
                if not last:
                    print(f"{DIM}{reply}{RESET}")
                history.append({"role": "assistant", "content": reply})
        except Exception as exc:
            print(f"{RED}{exc}{RESET}")
            return
    print()


def main() -> None:
    global SHOTS
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    persona = load_persona()
    SHOTS = load_examples()
    memory = Memory(MEMORY_DB)
    history = memory.recent()
    print(f"{DIM}{model} @ {SERVER} · {len(SHOTS)//2} examples loaded{RESET}")
    print(f"{DIM}{len(memory.facts())} facts · {len(history)//2} recent exchanges loaded{RESET}")
    print(f"{DIM}/test /model /reload /reset /remember /memory /forget /quit{RESET}\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not line:
            continue
        if line in ("/quit", "/exit"):
            return
        if line.startswith("/model"):
            bits = line.split(maxsplit=1)
            if len(bits) == 2:
                model, history = bits[1], []
                print(f"{DIM}now {model} · context cleared{RESET}")
            else:
                print(f"{DIM}current model: {model}{RESET}")
            continue
        if line == "/reload":
            persona = load_persona()
            SHOTS = load_examples()
            print(f"{DIM}reloaded · {len(persona)} chars · {len(SHOTS)//2} examples{RESET}")
            continue
        if line == "/reset":
            history = []
            print(f"{DIM}context cleared{RESET}")
            continue
        if line.startswith("/remember"):
            fact = line[len("/remember"):].strip()
            if not fact:
                print(f"{DIM}usage: /remember FACT{RESET}")
            else:
                fact_id = memory.remember(fact)
                print(f"{DIM}remembered [{fact_id}]{RESET}")
            continue
        if line == "/memory":
            facts = memory.facts()
            if not facts:
                print(f"{DIM}no durable facts stored{RESET}")
            for fact_id, fact in facts:
                print(f"{DIM}[{fact_id}]{RESET} {fact}")
            continue
        if line.startswith("/forget"):
            value = line[len("/forget"):].strip()
            if not value.isdigit():
                print(f"{DIM}usage: /forget ID{RESET}")
            elif memory.forget(int(value)):
                print(f"{DIM}forgotten{RESET}")
            else:
                print(f"{DIM}no memory with id {value}{RESET}")
            continue
        if line == "/test":
            run_tests(model, persona)
            continue

        memory_context = memory.context(line)
        history.append({"role": "user", "content": line})
        try:
            reply = ask(model, persona, history, memory_context=memory_context)
        except urllib.error.URLError as exc:
            print(f"{RED}{exc}{RESET}")
            print(f"{DIM}Is Ollama reachable at {SERVER}?{RESET}")
            history.pop()
            continue
        except Exception as exc:
            print(f"{RED}{exc}{RESET}")
            history.pop()
            continue
        history.append({"role": "assistant", "content": reply})
        memory.record(line, reply)
        history = history[-12:]


if __name__ == "__main__":
    main()
