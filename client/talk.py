#!/usr/bin/env python3
"""Type to Alfred locally and hear the selected RVC voice."""

import argparse
import base64
import io
import json
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

ROOT = Path(__file__).parent
REMOTE = "a1-4rd"
REMOTE_PROJECT = "~/a1-4rd"
VOICE_URL = "http://127.0.0.1:5051"

# How long to hold the silence after each sentence. Piper's own trailing pad is
# trimmed off first, so these are the whole pause and the only thing setting his
# tempo. Full stops are meant to sit; the character is in the pacing.
PAUSE = {".": 0.28, "!": 0.26, "?": 0.30, ",": 0.14, ";": 0.16, ":": 0.16, "—": 0.16}
DEFAULT_PAUSE = 0.18
SILENCE_FLOOR = 0.003   # amplitude below which a sample counts as silence
FADE_SECONDS = 0.005    # edge ramp, so a trimmed clip starts without a click
# What the voice server sends, and what the speakers run at, so Windows never
# converts. At 32 kHz WASAPI's on-the-fly converter made his voice crackle live,
# while the same audio was clean in a media player (2026-09-16).
SAMPLE_RATE = 48000
OUTPUT_BUFFER = 0.1     # seconds of audio the device holds; see open_output


def decode(data: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(data)) as clip:
        rate = clip.getframerate()
        pcm = np.frombuffer(clip.readframes(clip.getnframes()), dtype="<i2")
    return pcm.astype(np.float32) / 32768.0, rate


def trim(samples: np.ndarray, rate: int) -> np.ndarray:
    """Strip the silence Piper pads onto every clip, and fade the cut edges.

    Each clip arrived with up to 150ms of trailing silence. Played back to back
    that padding stacked with the gap between clips, which is most of what made
    him sound like he was buffering between sentences.
    """
    loud = np.flatnonzero(np.abs(samples) > SILENCE_FLOOR)
    if loud.size == 0:
        return samples[:0]
    margin = int(FADE_SECONDS * rate)
    body = samples[max(loud[0] - margin, 0):loud[-1] + 1 + margin].copy()
    edge = min(margin, body.size // 2)
    if edge:
        ramp = np.linspace(0.0, 1.0, edge, dtype=np.float32)
        body[:edge] *= ramp
        body[-edge:] *= ramp[::-1]
    return body


def open_output(buffer: float = None) -> sd.OutputStream:
    """The lowest-latency way to reach the default speakers, falling back to plain.

    PortAudio's default on this laptop is MME, which buffers 91ms before a sound
    is heard; WASAPI on the same speakers buffers 24ms (measured 2026-09-16).
    The voice now arrives at the device's own 48kHz, so auto_convert does
    nothing here; it stays only for a speaker running at some other rate. The
    microphone stays on MME: there it is the faster of the two (30ms against 60ms).

    That 24ms is also almost no margin. His voice grew crackly the longer a
    session ran, which is what a warm laptop missing a 24ms deadline sounds like,
    so the buffer is now OUTPUT_BUFFER. WASAPI ignores "high" here (still 22ms)
    but honours a number: 0.1 gives 110ms (measured 2026-09-17).
    """
    latency = OUTPUT_BUFFER if buffer is None else buffer
    try:
        wasapi = next(api for api in sd.query_hostapis() if "WASAPI" in api["name"])
        if wasapi["default_output_device"] >= 0:
            return sd.OutputStream(
                device=wasapi["default_output_device"], samplerate=SAMPLE_RATE, channels=1,
                dtype="float32", latency=latency,
                extra_settings=sd.WasapiSettings(auto_convert=True),
            )
    except (StopIteration, sd.PortAudioError, AttributeError, ValueError):
        pass
    return sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", latency=latency)


class Player(threading.Thread):
    """One continuous output stream, fed from a queue.

    winsound.PlaySound opened the device, played one sentence, closed it, and
    blocked the receive loop the whole time. That put a device round trip in
    every seam and stopped the client reading the socket while Alfred spoke.
    Here the stream stays open for the session and the network keeps running.
    """

    def __init__(self, pause_scale: float = 1.0, buffer: float = OUTPUT_BUFFER):
        super().__init__(daemon=True)
        self.queue: queue.Queue = queue.Queue()
        self.pause_scale = pause_scale
        self.deadline = 0.0
        # Times the device ran dry in the middle of a sentence. A dropout is heard
        # as a crackle, and this is the only way to tell one from a bad voice.
        self.dropouts = 0
        # Opening the device costs a few hundred milliseconds. Pay it now, while
        # the tunnel is coming up, rather than on his first sentence.
        self.stream = open_output(buffer)
        self.stream.start()
        self.start()

    def submit(self, audio: bytes, sentence: str) -> None:
        self.queue.put((audio, sentence))

    def drain(self) -> None:
        """Block until everything queued has actually finished playing."""
        done = threading.Event()
        self.queue.put(done)
        done.wait()

    def close(self) -> None:
        self.queue.put(None)
        self.join(timeout=10)

    def run(self) -> None:
        while True:
            item = self.queue.get()
            if item is None:
                break
            if isinstance(item, threading.Event):
                # Wait out the queued audio, plus whatever the device still
                # holds, so the last word is not clipped by the next prompt.
                remaining = self.deadline - time.perf_counter() + self.stream.latency
                if remaining > 0:
                    time.sleep(remaining)
                item.set()
                continue
            self._play(*item)
        self.stream.stop()
        self.stream.close()

    def _play(self, audio: bytes, sentence: str) -> None:
        samples, rate = decode(audio)
        if rate != SAMPLE_RATE:
            raise RuntimeError(f"expected {SAMPLE_RATE}Hz from the voice server, got {rate}Hz")
        pause = PAUSE.get(sentence.rstrip()[-1:], DEFAULT_PAUSE) * self.pause_scale
        block = np.concatenate([trim(samples, rate), np.zeros(int(pause * rate), dtype=np.float32)])
        # If the queue starved, the device has already drained and this block
        # starts now rather than where the last one was due to end.
        self.deadline = max(self.deadline, time.perf_counter()) + block.size / rate
        # Written in 20ms pieces: PortAudio reports an underflow on the write
        # after it happens, so one write per sentence would blame every dropout
        # on the silence between sentences. Only mid-sentence ones are counted.
        piece = int(0.02 * rate)
        for index, start in enumerate(range(0, block.size, piece)):
            if self.stream.write(block[start:start + piece]) and index > 0:
                self.dropouts += 1


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, text=True, **kwargs)


def chat(prompt: str, player, on_media=None) -> tuple[float, float, float]:
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
            if "media" in frame:
                # Something to play. It starts now, under his announcement,
                # because resolving the stream takes a couple of seconds anyway.
                if on_media is not None:
                    on_media(frame["media"])
                continue
            sentence = frame["text"]
            if first_audio is None:
                first_audio = time.perf_counter() - started
            print((" " if part else "") + sentence, end="", flush=True)
            total_tts += frame["tts_seconds"]
            total_rvc += frame["rvc_seconds"]
            part += 1
            if player is not None:
                player.submit(base64.b64decode(frame["audio"]), sentence)
    print()
    if player is not None:
        dropouts_before = getattr(player, "dropouts", 0)
        player.drain()
        dropped = getattr(player, "dropouts", 0) - dropouts_before
        if dropped:
            print(f"\033[2m  (audio dropped out {dropped} time{'s' if dropped != 1 else ''} mid-sentence: "
                  f"the laptop fell behind; try --buffer 0.2)\033[0m")
    return total_tts, total_rvc, first_audio or 0.0


def start_voice_tunnel() -> subprocess.Popen:
    run(
        ["ssh", REMOTE, f"cd {REMOTE_PROJECT} && (pgrep -f '[s]earx.webapp' >/dev/null || setsid -f ./scripts/searx-server.sh >rvc-output/searx.log 2>&1); (pgrep -f '[v]oice_server.py' >/dev/null || setsid -f ./scripts/voice-server.sh >rvc-output/voice-server.log 2>&1)"],
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
    parser.add_argument(
        "--pause", type=float, default=1.0,
        help="scale every inter-sentence pause; 1.4 is slower and more deliberate",
    )
    args = parser.parse_args()

    print("Alfred voice chat. Type /quit to leave.\n")
    tunnel = start_voice_tunnel()
    player = None if args.no_play else Player(pause_scale=args.pause)
    try:
        if args.prompt:
            tts_time, rvc_time, first_audio = chat(args.prompt, player)
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
                tts_time, rvc_time, first_audio = chat(prompt, player)
                print(f"[first audio {first_audio:.2f}s · TTS {tts_time:.2f}s · voice conversion {rvc_time:.2f}s]")
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or str(exc)).strip()
                print(f"Voice pipeline failed: {detail}", file=sys.stderr)
    finally:
        if player is not None:
            player.close()
        tunnel.terminate()


if __name__ == "__main__":
    main()
