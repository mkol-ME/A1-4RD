#!/usr/bin/env python3
"""Type to Alfred locally and hear the selected RVC voice."""

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import winsound
from pathlib import Path

ROOT = Path(__file__).parent
REMOTE = "a1-4rd"
REMOTE_PROJECT = "~/a1-4rd"
VOICE_URL = "http://127.0.0.1:5051"


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, text=True, **kwargs)


def chat(prompt: str, workdir: Path, play: bool) -> tuple[float, float, float]:
    request = urllib.request.Request(
        f"{VOICE_URL}/chat",
        data=json.dumps({"text": prompt}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    total_tts = 0.0
    total_rvc = 0.0
    started = time.perf_counter()
    first_audio = None
    part = 0
    print("Alfred: ", end="", flush=True)
    with urllib.request.urlopen(request, timeout=180) as response:
        for raw in response:
            frame = json.loads(raw)
            if frame.get("done"):
                break
            if "error" in frame:
                raise RuntimeError(frame["error"])
            sentence = frame["text"]
            if first_audio is None:
                first_audio = time.perf_counter() - started
            print((" " if part else "") + sentence, end="", flush=True)
            output = workdir / f"alfred-{part}.wav"
            output.write_bytes(base64.b64decode(frame["audio"]))
            total_tts += frame["tts_seconds"]
            total_rvc += frame["rvc_seconds"]
            part += 1
            if play:
                winsound.PlaySound(str(output), winsound.SND_FILENAME)
    print()
    return total_tts, total_rvc, first_audio or 0.0


def start_voice_tunnel() -> subprocess.Popen:
    run(
        ["ssh", REMOTE, f"cd {REMOTE_PROJECT} && (pgrep -f '[v]oice_server.py' >/dev/null || setsid -f ./voice-server.sh >rvc-output/voice-server.log 2>&1)"] ,
        capture_output=True,
    )
    tunnel = subprocess.Popen(
        ["ssh", "-N", "-L", "5051:127.0.0.1:5051", REMOTE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{VOICE_URL}/health", timeout=1) as response:
                if response.status == 200:
                    return tunnel
        except (OSError, urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    tunnel.terminate()
    raise RuntimeError("voice server did not become ready")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-play", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--prompt", help="speak one prompt and exit")
    args = parser.parse_args()

    print("Alfred voice chat. Type /quit to leave.\n")
    tunnel = start_voice_tunnel()
    try:
        with tempfile.TemporaryDirectory(prefix="alfred-talk-") as temp:
            workdir = Path(temp)
            if args.prompt:
                tts_time, rvc_time, first_audio = chat(args.prompt, workdir, not args.no_play)
                print(f"[first audio {first_audio:.2f}s · TTS {tts_time:.2f}s · voice conversion {rvc_time:.2f}s]")
                return
            while True:
                try:
                    prompt = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                if prompt in ("/quit", "/exit"):
                    return
                if not prompt:
                    continue
                try:
                    tts_time, rvc_time, first_audio = chat(prompt, workdir, not args.no_play)
                    print(f"[first audio {first_audio:.2f}s · TTS {tts_time:.2f}s · voice conversion {rvc_time:.2f}s]")
                except subprocess.CalledProcessError as exc:
                    detail = (exc.stderr or exc.stdout or str(exc)).strip()
                    print(f"Voice pipeline failed: {detail}", file=sys.stderr)
    finally:
        tunnel.terminate()


if __name__ == "__main__":
    main()
