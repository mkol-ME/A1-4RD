#!/usr/bin/env python3
"""Speak to Alfred and have him answer aloud.

The wake word is not a trained model. Everything the microphone hears gets
transcribed anyway — Whisper runs at ten times real time on the 1060 and the
box is otherwise idle — and the transcript is checked for his name. That costs
a few hundred milliseconds of GPU per utterance and buys an exact custom wake
word with nothing to train, which no small off-the-shelf model offers for
"Alfred". If it ever needs to run on a Pi with the box asleep, that trade
changes and this is the piece to replace.

Nothing leaves the LAN: the audio goes over the same SSH tunnel as everything
else, and is transcribed on the user's own machine.
"""

import argparse
import collections
import io
import json
import queue
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

import numpy as np
import sounddevice as sd

import talk

RATE = 16000            # what Whisper wants; resampling anywhere else is wasted work
FRAME = 480             # 30ms
WHISPER_URL = "http://127.0.0.1:5052"

CALIBRATION_SECONDS = 1.0
# Speech has to beat the room by this much. Measured against the noise floor
# rather than a fixed number, because a desk fan moves the floor a long way.
SPEECH_MARGIN = 4.0
FLOOR_MINIMUM = 0.004
# Long enough not to split an ordinary hesitation, but short enough that the
# handoff feels immediate.  At 0.55s every turn had a conspicuous half-second
# pause before transcription could even begin.
SILENCE_HANGOVER = 0.40
# Kept rolling so the utterance can start before the microphone noticed it had.
# Speech crosses the threshold a syllable in, not at the attack, and everything
# before that was being thrown away: "co-main event" came back as "Comade".
# Three hundred milliseconds of hindsight costs nothing and buys the first word.
PREROLL_SECONDS = 0.3
# Player.drain() already waits through the punctuation pause appended after the
# final clip (normally 0.26-0.30s).  This is only a small extra guard for device
# latency and room echo; the old 0.35s stacked another full pause on top.
SETTLE_SECONDS = 0.08
MIN_UTTERANCE = 0.35    # shorter than this is a cough or a keyboard
MAX_UTTERANCE = 15.0

# What Whisper actually produces when someone says "Alfred" — it has no idea
# the word is a name, so it reaches for words it knows.
WAKE_WORDS = ("alfred", "alfie", "alford", "elfred", "alfredo", "al fred")
WAKE_WINDOW_WORDS = 3   # his name has to be near the front, not buried mid-sentence

# Saying his name before every single sentence is not a conversation, it is a
# summons repeated. His name opens one; after that he is simply present, the way
# a man standing in the room is, until he is dismissed or the room goes quiet.
DISMISSALS = (
    "that will be all", "that'll be all", "that's all", "thats all", "that is all",
    "go to sleep", "goodnight", "good night", "nevermind", "never mind",
    "dismissed", "stand down", "leave me", "leave me be", "you can go",
)
# How long he stays in the room with nothing said to him. Long enough to read
# what he said, try it on the printer, and come back with the next question;
# short enough that a conversation from lunchtime is not still open at dinner.
ATTENTION_SECONDS = 180.0


def rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(block))) if block.size else 0.0)


def to_wav(samples: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes((np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes())
    return buffer.getvalue()


def transcribe(samples: np.ndarray) -> tuple[str, float]:
    request = urllib.request.Request(
        f"{WHISPER_URL}/transcribe", data=to_wav(samples),
        headers={"Content-Type": "audio/wav"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read())
    return payload["text"], payload["seconds"]


def plain_words(text: str) -> list[str]:
    """Bare lowercase tokens, keeping digits, accents, decimals and P1S whole."""
    return re.findall(r"[^\W_]+(?:[.'][^\W_]+)*", text.lower())


def is_dismissal(prompt: str) -> bool:
    """Has he just been told to stop listening?

    Matched on the whole utterance rather than anywhere inside it, because
    "nevermind the brim, why is it lifting" is a question, not a dismissal.
    His name is allowed on either end, since that is how anyone says it.
    """
    words = plain_words(prompt)
    while words and words[0] in WAKE_WORDS:
        words = words[1:]
    while words and words[-1] in WAKE_WORDS:
        words = words[:-1]
    if words and words[0] in ("ok", "okay", "alright", "right", "well"):
        words = words[1:]
    return " ".join(words) in DISMISSALS


def strip_wake_word(text: str) -> str | None:
    """The prompt with his name removed, or None if he was not addressed.

    Returns bare lowercase words, which looks lossy and is not: the user types to
    him in lowercase without punctuation, and examples.md is deliberately written
    in that same register because tidied-up exemplars made him correct correct
    usage. Speech arriving as "Why does my first layer lift?" would be the odd
    one out, not the transcript.

    It was lossy in one way that mattered. The pattern was [a-z']+, so every
    digit was deleted on the way through: Whisper heard "Pokemon number 25"
    perfectly and Alfred was handed "pokemon number", then blamed for not
    knowing. Accented letters went the same way, which turned "Pokémon" into
    "pok mon". Keep anything that is a letter or a digit, and keep the joiners
    inside a token so "0.4", "p1s" and "don't" survive whole.
    """
    words = plain_words(text)
    for position in range(min(WAKE_WINDOW_WORDS, len(words))):
        pair = " ".join(words[position:position + 2])
        if pair in WAKE_WORDS:
            return " ".join(words[position + 2:])
        if words[position] in WAKE_WORDS:
            return " ".join(words[position + 1:])
    return None


class Microphone:
    """Blocks of audio, and a noise floor measured from this actual room."""

    def __init__(self, device=None):
        self.blocks: queue.Queue = queue.Queue()
        self.preroll: collections.deque = collections.deque(
            maxlen=max(1, int(PREROLL_SECONDS * RATE / FRAME)))
        # Set while Alfred is speaking. His voice arrives at this microphone
        # like anyone else's, and it was being transcribed and answered: "Indeed,
        # sir." and "Ahem." both came back as things someone had said to him.
        # Draining the queue afterwards was not enough, because the tail of a
        # sentence lands in it after the drain. So he simply does not listen
        # while he talks, which is also the polite arrangement.
        self.deaf = False
        self.stream = sd.InputStream(
            samplerate=RATE, channels=1, dtype="float32",
            blocksize=FRAME, device=device, callback=self._on_audio,
        )
        self.stream.start()
        self.floor = self._calibrate()

    def _on_audio(self, indata, frames, timestamp, status):
        if self.deaf:
            return
        self.blocks.put(indata[:, 0].copy())

    def _calibrate(self) -> float:
        levels = []
        deadline = time.perf_counter() + CALIBRATION_SECONDS
        while time.perf_counter() < deadline:
            try:
                levels.append(rms(self.blocks.get(timeout=1.0)))
            except queue.Empty:
                break
        floor = float(np.median(levels)) if levels else FLOOR_MINIMUM
        return max(floor, FLOOR_MINIMUM)

    def flush(self) -> None:
        """Throw away everything captured while Alfred was talking."""
        while not self.blocks.empty():
            try:
                self.blocks.get_nowait()
            except queue.Empty:
                break
        self.preroll.clear()

    def settle(self, seconds: float = SETTLE_SECONDS) -> None:
        """Let the room stop ringing, then start listening again."""
        time.sleep(seconds)
        self.flush()
        self.deaf = False

    def next_utterance(self, timeout: float = 2.0) -> np.ndarray | None:
        """Collect from the first loud block until the pause after it.

        Returns None if the microphone stops producing. A live stream never
        stops, so this only fires if the device has gone away — but without it
        a rejected utterance drops into a blocking read and the whole loop
        hangs there silently, which is exactly what it did the first time.
        """
        threshold = self.floor * SPEECH_MARGIN
        collected, silence, started = [], 0.0, False
        while True:
            try:
                block = self.blocks.get(timeout=timeout)
            except queue.Empty:
                return None
            level = rms(block)
            if not started:
                if level < threshold:
                    self.preroll.append(block)
                    continue
                started = True
                collected.extend(self.preroll)   # the word that started it
                self.preroll.clear()
                collected.append(block)
                continue
            collected.append(block)
            silence = silence + FRAME / RATE if level < threshold else 0.0
            length = len(collected) * FRAME / RATE
            if silence >= SILENCE_HANGOVER or length >= MAX_UTTERANCE:
                if length - silence < MIN_UTTERANCE:
                    collected, silence, started = [], 0.0, False
                    self.preroll.clear()
                    continue
                return np.concatenate(collected)

    def close(self) -> None:
        self.stream.stop()
        self.stream.close()


def start_tunnels() -> subprocess.Popen:
    """Both services up on the box, both ports forwarded over one connection."""
    talk.run(
        ["ssh", talk.REMOTE,
         f"cd {talk.REMOTE_PROJECT} && "
         f"(pgrep -f '[s]earx.webapp' >/dev/null || setsid -f ./searx-server.sh >rvc-output/searx.log 2>&1); "
         f"(pgrep -f '[v]oice_server.py' >/dev/null || setsid -f ./voice-server.sh >rvc-output/voice-server.log 2>&1); "
         f"(pgrep -f '[w]hisper_server.py' >/dev/null || setsid -f ./whisper-server.sh >rvc-output/whisper-server.log 2>&1)"],
        capture_output=True,
    )
    tunnel = subprocess.Popen(
        ["ssh", "-N", "-L", "5051:127.0.0.1:5051", "-L", "5052:127.0.0.1:5052", talk.REMOTE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for url in (talk.VOICE_URL, WHISPER_URL):
        for _ in range(90):
            try:
                with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, urllib.error.URLError, TimeoutError):
                time.sleep(0.5)
        else:
            tunnel.terminate()
            raise RuntimeError(f"{url} did not become ready")
    return tunnel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true",
                        help="answer everything, without waiting to be addressed")
    parser.add_argument("--attention", type=float, default=ATTENTION_SECONDS,
                        help="seconds he keeps listening after a reply, before his name is needed again")
    parser.add_argument("--pause", type=float, default=1.0, help="scale his inter-sentence pauses")
    parser.add_argument("--device", help="input device name or index")
    args = parser.parse_args()

    device = args.device
    if device is not None and device.isdigit():
        device = int(device)

    tunnel = start_tunnels()
    player = talk.Player(pause_scale=args.pause)
    microphone = Microphone(device)
    print(f"Listening. Noise floor {microphone.floor:.4f}, speaking above {microphone.floor * SPEECH_MARGIN:.4f}.")
    if args.open:
        print("Open mic — no wake word.")
    else:
        print("Say \"Alfred\" to start. He then stays listening; "
              "\"that'll be all\" sends him away.")
    print("Ctrl-C to stop.\n")
    attentive_until = 0.0
    try:
        while True:
            audio = microphone.next_utterance()
            if audio is None:
                continue
            heard, seconds = transcribe(audio)
            if not heard:
                continue
            prompt = heard if args.open else strip_wake_word(heard)
            summoned = prompt is not None
            if not summoned and time.monotonic() < attentive_until:
                # Already in the room. Nobody says "Alfred" to a man they are
                # mid-conversation with.
                prompt = " ".join(plain_words(heard))
            if not prompt or not prompt.strip():
                if summoned:
                    prompt = "yes?"                # his name, and nothing after it
                else:
                    print(f"  {talk_dim(heard)}")  # heard, but not addressed to him
                    continue
            if not args.open and is_dismissal(prompt):
                print(f"You: {prompt}")
                microphone.deaf = True
                try:
                    talk.chat(prompt, player)
                except Exception as exc:
                    print(f"  reply failed: {exc}", file=sys.stderr)
                finally:
                    microphone.settle()
                attentive_until = 0.0
                print(talk_dim("  — say \"Alfred\" when you want him again —") + "\n")
                continue
            print(f"You: {prompt}   [{len(audio) / RATE:.1f}s audio, {seconds:.2f}s to transcribe]")
            microphone.deaf = True                 # he does not listen while he talks
            try:
                talk.chat(prompt, player)
            except Exception as exc:
                print(f"  reply failed: {exc}", file=sys.stderr)
            finally:
                microphone.settle()
            if not args.open:
                attentive_until = time.monotonic() + args.attention
    except KeyboardInterrupt:
        print()
    finally:
        microphone.close()
        player.close()
        tunnel.terminate()


def talk_dim(text: str) -> str:
    return f"\033[2m({text})\033[0m"


if __name__ == "__main__":
    main()
