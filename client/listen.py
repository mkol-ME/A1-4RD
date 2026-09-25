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
else, and is transcribed on the owner's own machine.
"""

import argparse
import base64
import collections
import io
import json
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import sounddevice as sd

import talk
from music import Jukebox, MusicPlayer, SpotifyRemote

# The two confirmations the client says on its own. They are his wording, which
# lives on his server and nowhere else, so they are fetched from it rather than
# kept in a file here. Fetched on first use, not at import: the tunnel to him is
# not up yet when this module loads. If he cannot be reached there is nothing to
# confirm anyway, and the plain stand-ins still show the switch happened.
_WORDING: dict = {}


def wording() -> dict:
    if not _WORDING:
        try:
            with urllib.request.urlopen(f"{talk.VOICE_URL}/lines", timeout=3) as response:
                _WORDING.update(json.load(response))
        except Exception:
            _WORDING.update({"language_english": {"en": "English."},
                             "language_portuguese": {"pt": "Português."}})
    return _WORDING


RATE = 16000            # what Whisper wants; resampling anywhere else is wasted work
FRAME = 480             # 30ms
WHISPER_URL = "http://127.0.0.1:5052"

CALIBRATION_SECONDS = 1.0
# Speech has to beat the room by this much. Measured against the noise floor
# rather than a fixed number, because a desk fan moves the floor a long way.
SPEECH_MARGIN = 4.0
FLOOR_MINIMUM = 0.004
# Long enough not to split an ordinary hesitation, but short enough that the
# handoff feels immediate. At 0.55s every turn had a conspicuous half-second
# pause before transcription could even begin — but that was before early
# transcription, which now overlaps most of the wait. At 0.40s, in the second
# real session (2026-09-16), he kept answering before the owner had finished:
# a pause after a complete-sounding phrase ended the turn, and since he does not
# listen while he talks, the rest of the sentence was simply lost. Being cut off
# is worse than 0.2s more wait. Tune with --hangover rather than editing this.
SILENCE_HANGOVER = 0.60
# Whisper does not have to wait for the hangover to be sure. At this much
# silence the utterance so far goes off to be transcribed; if the pause runs on
# to SILENCE_HANGOVER that transcript is the one used, and if he was only
# drawing breath it is thrown away. Nothing is cut sooner than before — the
# ~0.3s of transcription just overlaps the wait instead of following it.
EARLY_TRANSCRIBE_SILENCE = 0.20
# 0.40s is right for a finished sentence and wrong for a man looking for the
# next word: in the first real session "what should i have [pause] for dinner",
# "it's 92 [pause] degrees outside" and "what's the gravitational [pause]
# constant" were each cut in two and answered as fragments. So at the hangover
# the early transcript is read, and if it stops somewhere no sentence stops, he
# is given up to this long to carry on. A finished sentence ends exactly as fast
# as before, because the transcript was already being waited for.
UNFINISHED_HANGOVER = 1.2
# Words an English sentence does not end on. A question can technically end on
# "have" or "in" ("what do you have", "who's in"), and the cost of that is only
# the longer wait, never a cut.
DANGLING = {
    "a", "an", "the", "my", "your", "his", "her", "its", "our", "their", "this", "that", "these",
    "those", "some", "any", "every", "each", "no",
    "in", "on", "at", "of", "to", "for", "from", "with", "about", "into", "onto", "by", "as",
    "than", "like", "between", "through", "over", "under", "after", "before", "around",
    "and", "or", "but", "so", "because", "if", "when", "while", "whether", "then",
    "is", "are", "was", "were", "be", "been", "am", "have", "has", "had", "does", "did",
    "will", "would", "can", "could", "should", "shall", "might", "must", "may",
    "i", "i'm", "we", "they", "he", "she", "what's", "whats", "how's", "where's", "who's",
    "um", "uh", "er", "erm",
}
DETERMINERS = {"a", "an", "the", "my", "your", "his", "her", "its", "our", "their", "this", "that", "some"}
ADJECTIVE_ENDINGS = ("al", "ic", "ical", "ous", "ive", "ful", "less", "able", "ible", "ary", "ent", "ant")
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
# With music playing through the laptop speakers the room never goes quiet, so
# an utterance would only ever end at MAX_UTTERANCE. Cut it into short windows
# instead and listen for his name in each: "Alfred, pause" is heard within a few
# seconds rather than fifteen. Once his name is heard the music ducks, and the
# command after it is heard cleanly.
MUSIC_UTTERANCE = 3.0
INSTANCE_PORT = 5049      # held while listen.py runs, so a second copy refuses to start
# While he is talking the laptop still listens, in windows this long, for his
# name and nothing else: "Alfred" over a reply stops it. A whole card read out at
# once could not be stopped except by closing the program (2026-09-24). His own
# voice from the speakers is heard too, but it never says his name.
BARGE_WINDOW = 2.5
# Said after his name to stop him, rather than to ask something new.
STOP_WORDS = {"stop", "stop it", "stop talking", "ok", "okay", "enough", "thats enough", "that's enough",
              "quiet", "shush", "shut up", "hold on", "wait", "hang on", "pause", "cancel", "never mind",
              "nevermind", "thanks", "thank you", "got it", "alright"}
# After his name alone while music plays, how long the next words count as
# addressed to him without saying it again.
MUSIC_ADDRESS_SECONDS = 8.0

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
    # Brazilian Portuguese
    "é só isso", "e so isso", "só isso", "so isso", "pode ir", "boa noite", "tchau", "pode descansar",
    "obrigado é só isso", "obrigado e so isso",
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


# The language he listens and answers in, changed only by saying so: "speak
# Portuguese" / "fala português", and "speak English" / "volta pro inglês".
# Guessing it per turn was tried first and switched unreliably (2026-09-17).
LISTEN_LANGUAGE = ["en"]
# Any form of the verb, because Whisper does not keep tense: "switch to Portuguese"
# came back as "Alfred switched to Portuguese", matched nothing, and he answered in
# Portuguese through his English voice with his ears still in English (2026-09-17).
_SWITCH_VERBS = (r"speak\w*|spoke|talk\w*|switch\w*|chang\w*|answer\w*|repl\w*|use|using|go|going|"
                 r"fala\w*|fale|muda\w*|mude|troca\w*|troque|modo")
TO_PORTUGUESE = re.compile(rf"\b(?:{_SWITCH_VERBS})\b.*\bportugu", re.I)
TO_ENGLISH = re.compile(
    rf"\b(?:{_SWITCH_VERBS}|back|volta\w*|volte)\b.*\b(?:english|ingles)\b", re.I)


def language_command(prompt: str) -> str | None:
    """"pt" or "en" if this turn asks to change language, else None."""
    text = unicodedata.normalize("NFKD", prompt.lower()).encode("ascii", "ignore").decode()
    text = " ".join(word for word in re.findall(r"[a-z]+", text) if word != "alfred")
    if text in ("portuguese", "em portugues", "portugues", "portuguese mode", "portuguese please"):
        return "pt"
    if text in ("english", "em ingles", "ingles", "english mode", "english please"):
        return "en"
    if len(text.split()) > 8:
        return None                     # a sentence that mentions a language, not a command
    if TO_PORTUGUESE.search(text):
        return "pt"
    if TO_ENGLISH.search(text):
        return "en"
    return None


def keep_clip(samples: np.ndarray, text: str, language: str) -> None:
    """Hand the finished utterance to the server's archive. Never worth failing a turn for."""
    body = json.dumps({"audio": base64.b64encode(to_wav(samples)).decode("ascii"),
                       "text": text, "language": language}).encode("utf-8")
    request = urllib.request.Request(f"{WHISPER_URL}/keep", data=body,
                                     headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=30).close()
    except Exception:
        pass


def transcribe(samples: np.ndarray) -> tuple[str, float, str]:
    """Text, seconds taken, and the language Whisper heard ("en" or "pt")."""
    request = urllib.request.Request(
        f"{WHISPER_URL}/transcribe?mode={LISTEN_LANGUAGE[0]}", data=to_wav(samples),
        headers={"Content-Type": "audio/wav"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read())
    return payload["text"], payload["seconds"], payload.get("language", "en")


class EarlyTranscript:
    """The transcription started at the first sign of a pause, if it is still good.

    Each new pause replaces the last one's request; only the most recent can
    belong to the utterance that ends, because any earlier pause was followed
    by more speech.
    """

    def __init__(self, transcribe_fn=None):
        self.transcribe = transcribe_fn or transcribe
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.pending = None

    def start(self, samples: np.ndarray) -> None:
        self.pending = self.pool.submit(self.transcribe, samples)

    def peek(self, wait: float = 1.0) -> str | None:
        """The pending transcript's text, waiting briefly for it; None if there is none."""
        if self.pending is None:
            return None
        try:
            return self.pending.result(timeout=wait)[0]
        except Exception:
            return None

    def take(self, audio: np.ndarray, ended_by_silence: bool) -> tuple[str, float]:
        """The early result when it covers this utterance, else transcribe it now."""
        pending, self.pending = self.pending, None
        if pending is not None and ended_by_silence:
            try:
                return pending.result()
            except Exception:
                pass                      # fall through and ask again, the old way
        return self.transcribe(audio)


def sounds_unfinished(text: str | None) -> bool:
    """Does this transcript stop somewhere a sentence does not?

    Whisper punctuates everything, "What's the gravitational?" included, so its
    full stops and question marks mean nothing here; the words decide. Unsure
    means finished: the old behaviour is the fallback, not a longer wait.
    """
    if not text or not text.strip():
        return False
    stripped = text.strip()
    if stripped.endswith(("-", "—", "...", "…")):
        return True                               # Whisper's own mark for a cut-off word
    words = plain_words(stripped)
    while words and words[-1] in WAKE_WORDS:      # "it's 92, alfred" still ends on 92
        words = words[:-1]
    if not words:
        return False
    if words[-1] in DANGLING:
        return True
    # "the gravitational", "a magnetic": a determiner then one describing word.
    return (len(words) >= 2 and words[-2] in DETERMINERS
            and words[-1].endswith(ADJECTIVE_ENDINGS))


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

    Returns bare lowercase words, which looks lossy and is not: the owner types to
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

    def next_utterance(self, timeout: float = 2.0, on_pause=None, unfinished=None,
                       max_length: float = MAX_UTTERANCE, stop=None, idle=None) -> np.ndarray | None:
        """Collect from the first loud block until the pause after it.

        Returns None if the microphone stops producing. A live stream never
        stops, so this only fires if the device has gone away — but without it
        a rejected utterance drops into a blocking read and the whole loop
        hangs there silently, which is exactly what it did the first time.

        on_pause is handed the audio so far each time a pause reaches
        EARLY_TRANSCRIBE_SILENCE. Afterwards `ended_by_silence` says whether the
        latest of those pauses is the one that ended the utterance, and
        `longest_pause` is the longest gap he left inside it without being cut.

        unfinished is asked, once per pause, when that pause reaches
        SILENCE_HANGOVER. If it says the words so far trail off, the pause may
        run to UNFINISHED_HANGOVER before the utterance is called over, and
        `bridged` counts how many times that let him carry on.

        stop, if given, is asked after every block; once it says so, None comes
        back straight away (the reply being listened over has finished).

        idle, if given, is asked the same way but only while nobody is talking,
        so something waiting to be said never cuts into his sentence.
        """
        threshold = self.floor * SPEECH_MARGIN
        collected, silence, started = [], 0.0, False
        self.ended_by_silence, self.longest_pause, self.bridged = False, 0.0, 0
        limit = SILENCE_HANGOVER
        while True:
            try:
                block = self.blocks.get(timeout=timeout)
            except queue.Empty:
                return None
            if stop is not None and stop():
                return None
            level = rms(block)
            if not started:
                if idle is not None and idle():
                    return None
                if level < threshold:
                    self.preroll.append(block)
                    continue
                started = True
                collected.extend(self.preroll)   # the word that started it
                self.preroll.clear()
                collected.append(block)
                continue
            collected.append(block)
            if level < threshold:
                silence += FRAME / RATE
            else:
                if limit > SILENCE_HANGOVER and silence >= SILENCE_HANGOVER:
                    self.bridged += 1               # he did carry on after all
                self.longest_pause = max(self.longest_pause, silence)
                silence, limit = 0.0, SILENCE_HANGOVER
            length = len(collected) * FRAME / RATE
            if (on_pause is not None and silence >= EARLY_TRANSCRIBE_SILENCE
                    and silence - FRAME / RATE < EARLY_TRANSCRIBE_SILENCE
                    and length - silence >= MIN_UTTERANCE):
                on_pause(np.concatenate(collected))
            if (unfinished is not None and limit == SILENCE_HANGOVER
                    and silence >= SILENCE_HANGOVER and length - silence >= MIN_UTTERANCE
                    and length < max_length and unfinished()):
                limit = UNFINISHED_HANGOVER
            if silence >= limit or length >= max_length:
                if length - silence < MIN_UTTERANCE:
                    collected, silence, started = [], 0.0, False
                    self.longest_pause, limit = 0.0, SILENCE_HANGOVER
                    self.preroll.clear()
                    continue
                self.ended_by_silence = silence >= SILENCE_HANGOVER
                return np.concatenate(collected)

    def close(self) -> None:
        self.stream.stop()
        self.stream.close()


def start_tunnels() -> subprocess.Popen:
    """Both services up on the box, both ports forwarded over one connection."""
    talk.run(
        ["ssh", talk.REMOTE,
         f"cd {talk.REMOTE_PROJECT} && "
         f"(pgrep -f '[s]earx.webapp' >/dev/null || setsid -f ./scripts/searx-server.sh >rvc-output/searx.log 2>&1); "
         f"(pgrep -f '[v]oice_server.py' >/dev/null || setsid -f ./scripts/voice-server.sh >rvc-output/voice-server.log 2>&1); "
         f"(pgrep -f '[w]hisper_server.py' >/dev/null || setsid -f ./scripts/whisper-server.sh >rvc-output/whisper-server.log 2>&1); "
         f"(pgrep -f '[m]edia_server.py' >/dev/null || setsid -f ./scripts/media-server.sh >rvc-output/media-server.log 2>&1)"],
        capture_output=True,
    )
    # The media service is forwarded too, but not waited for: without it he
    # still talks, he just cannot play anything.
    tunnel = subprocess.Popen(
        ["ssh", "-N", "-L", "5051:127.0.0.1:5051", "-L", "5052:127.0.0.1:5052",
         "-L", "5053:127.0.0.1:5053", talk.REMOTE],
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


PENDING_EVERY = 8.0       # seconds between asks for something finished while he was away


def watch_pending(waiting: queue.Queue) -> None:
    """Ask the server, now and then, whether a tool has finished something to say.

    The server answers one request at a time, so this can sit behind a whole turn.
    It waits that out rather than timing out: a line is handed out only once,
    and one sent to a request that had already given up would be lost.
    """
    while True:
        try:
            with urllib.request.urlopen(f"{talk.VOICE_URL}/pending", timeout=600) as response:
                for line in json.loads(response.read()).get("lines", []):
                    waiting.put(line)
        except (OSError, ValueError):
            pass
        time.sleep(PENDING_EVERY)


def sentences_of(text: str) -> list[str]:
    return [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part]


def main() -> None:
    global SILENCE_HANGOVER, UNFINISHED_HANGOVER
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true",
                        help="answer everything, without waiting to be addressed")
    parser.add_argument("--attention", type=float, default=ATTENTION_SECONDS,
                        help="seconds he keeps listening after a reply, before his name is needed again")
    parser.add_argument("--pause", type=float, default=1.0, help="scale his inter-sentence pauses")
    parser.add_argument("--device", help="input device name or index")
    parser.add_argument("--hangover", type=float, default=SILENCE_HANGOVER,
                        help="seconds of silence that end your turn; raise it if he cuts you off, "
                             "lower it if he feels slow to answer")
    parser.add_argument("--buffer", type=float, default=talk.OUTPUT_BUFFER,
                        help="seconds of audio the speaker holds; raise it if his voice crackles")
    args = parser.parse_args()

    # One Alfred at a time. A second copy started while the first runs finds the
    # tunnel ports already forwarded, passes its health checks through the first
    # copy's tunnel, and then both listen and both answer over each other.
    try:
        instance_lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        instance_lock.bind(("127.0.0.1", INSTANCE_PORT))
    except OSError:
        print("Alfred is already running in another window. Close that one first.")
        # Refusing to start is not the ordinary goodbye. Exit non-zero so the
        # launcher holds the window open: on a double-click the console dies with
        # the process, and a clean exit took the line above with it.
        sys.exit(1)

    # The unfinished-sentence allowance keeps its margin over the normal one.
    UNFINISHED_HANGOVER = max(UNFINISHED_HANGOVER, args.hangover + 0.6)
    SILENCE_HANGOVER = args.hangover

    device = args.device
    if device is not None and device.isdigit():
        device = int(device)

    tunnel = start_tunnels()
    player = talk.Player(pause_scale=args.pause, buffer=args.buffer)
    microphone = Microphone(device)
    print(f"Listening. Noise floor {microphone.floor:.4f}, speaking above {microphone.floor * SPEECH_MARGIN:.4f}.")
    if args.open:
        print("Open mic — no wake word.")
    else:
        print("Say \"Alfred\" to start. He then stays listening; "
              "\"that'll be all\" sends him away.")
    print("Ctrl-C to stop.\n")
    attentive_until = 0.0
    addressed_until = 0.0          # his name alone was heard over music
    early = EarlyTranscript()
    archive = ThreadPoolExecutor(max_workers=1)
    music = Jukebox(MusicPlayer(), SpotifyRemote(talk.VOICE_URL))
    waiting = queue.Queue()
    threading.Thread(target=watch_pending, args=(waiting,), daemon=True).start()

    def say_waiting() -> bool:
        """Say whatever finished while he was quiet. True if anything was said."""
        lines = []
        while not waiting.empty():
            lines.append(waiting.get())
        if not lines:
            return False
        microphone.deaf = True
        music.duck()
        try:
            for line in lines:
                print(f"Alfred: {line}   [unasked]")
                for sentence in sentences_of(line):
                    player.submit(talk.speak(sentence), sentence)   # tools report in English
            player.drain()
        except Exception as exc:
            print(f"  (could not say it: {exc})", file=sys.stderr)
        finally:
            music.unduck()
            microphone.settle()
        return True

    def listen_for_name(done: threading.Event, cancel: threading.Event, after: list) -> None:
        """While he talks: stop him if his name is heard, keeping what followed it."""
        while not done.is_set():
            audio = microphone.next_utterance(timeout=0.5, max_length=BARGE_WINDOW, stop=done.is_set)
            if audio is None or done.is_set():
                continue
            try:
                heard = transcribe(audio)[0]
            except Exception:
                continue
            rest = strip_wake_word(heard or "")
            if rest is None:
                continue                          # his own voice, or the room
            after.append(rest)
            cancel.set()
            player.interrupt()
            return

    def reply(prompt: str) -> str | None:
        """Answer one prompt. If he says "Alfred" over the answer it stops there, and
        whatever he said after the name comes back as the next prompt."""
        music.duck()
        done, cancel, after = threading.Event(), threading.Event(), []
        microphone.flush()
        microphone.deaf = False                # listening only for his name, see BARGE_WINDOW
        watcher = threading.Thread(target=listen_for_name, args=(done, cancel, after), daemon=True)
        watcher.start()
        try:
            talk.chat(prompt, player, on_media=music.play, language=LISTEN_LANGUAGE[0], cancel=cancel)
        except Exception as exc:
            print(f"  reply failed: {exc}", file=sys.stderr)
        finally:
            done.set()
            watcher.join(timeout=5)
            microphone.deaf = True
            music.unduck()
            microphone.settle()
        if not cancel.is_set():
            return None
        rest = (after[0] if after else "").strip()
        print(talk_dim("interrupted"))
        return rest if rest and rest not in STOP_WORDS else None

    def converse(prompt: str) -> None:
        """A reply, and another for whatever he says over it, until one runs its course."""
        while prompt:
            prompt = reply(prompt)
            if prompt:
                print(f"You: {prompt}   [over him]")

    def switch_language(prompt: str) -> bool:
        """"Speak Portuguese" / "speak English": change language, say so, and stop there."""
        wanted = language_command(prompt)
        if wanted is None:
            return False
        LISTEN_LANGUAGE[0] = wanted
        said = wording()
        line = said["language_portuguese"]["pt"] if wanted == "pt" else said["language_english"]["en"]
        print(f"You: {prompt}   [language: {'Portuguese' if wanted == 'pt' else 'English'}]")
        microphone.deaf = True
        try:
            print(f"Alfred: {line}")
            player.submit(talk.speak(line, wanted), line)
            player.drain()
        except Exception as exc:
            print(f"  (could not say it: {exc})", file=sys.stderr)
        finally:
            microphone.settle()
        return True

    try:
        while True:
            audio = microphone.next_utterance(
                on_pause=early.start, unfinished=lambda: sounds_unfinished(early.peek()),
                max_length=MUSIC_UTTERANCE if music.active else MAX_UTTERANCE,
                idle=lambda: not waiting.empty())
            if audio is None:
                early.pending = None
                if say_waiting() and not args.open:
                    attentive_until = time.monotonic() + args.attention   # so he can answer it
                continue
            heard, seconds, *_ = early.take(audio, microphone.ended_by_silence)
            if not heard:
                continue
            # Kept for a better Whisper later and for learning whose voice it is.
            # Off the critical path: he is already being answered while it uploads.
            archive.submit(keep_clip, audio, heard, LISTEN_LANGUAGE[0])
            if addressed_until and time.monotonic() >= addressed_until:
                music.unduck()                     # his name, then nothing: music back up
                addressed_until = 0.0
            if music.active:
                # Lyrics are not requests. Over music only his name counts, or
                # the few seconds after his name was said on its own.
                prompt = strip_wake_word(heard)
                if prompt is None and addressed_until:
                    prompt = " ".join(plain_words(heard))
                if prompt is None:
                    continue
                if not prompt.strip():
                    if not addressed_until:
                        music.duck()
                    addressed_until = time.monotonic() + MUSIC_ADDRESS_SECONDS
                    print(talk_dim("  — listening, music lowered —"))
                    continue
                if addressed_until:
                    music.unduck()
                    addressed_until = 0.0
                if switch_language(prompt):
                    continue
                action = music.control(prompt)
                if action is not None:
                    print(f"You: {prompt}   [music: {action}]")
                    music.apply(action)
                    continue
                print(f"You: {prompt}   [over music]")
                converse(prompt)
                continue
            if addressed_until:                     # the music ended while he was addressed
                music.unduck()
                addressed_until = 0.0
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
            if switch_language(prompt):
                if not args.open:
                    attentive_until = time.monotonic() + args.attention
                continue
            if not args.open and is_dismissal(prompt):
                print(f"You: {prompt}")
                reply(prompt)
                attentive_until = 0.0
                print(talk_dim("  — say \"Alfred\" when you want him again —") + "\n")
                continue
            print(f"You: {prompt}   [{len(audio) / RATE:.1f}s audio, {seconds:.2f}s to transcribe, "
                  f"longest pause {microphone.longest_pause:.2f}s of {SILENCE_HANGOVER:.2f}s allowed"
                  f"{f', waited through {microphone.bridged} unfinished pause(s)' if microphone.bridged else ''}]")
            converse(prompt)
            if not args.open:
                attentive_until = time.monotonic() + args.attention
    except KeyboardInterrupt:
        print()
    finally:
        music.player.stop()        # Spotify plays in its own app; closing this leaves it be
        microphone.close()
        player.close()
        tunnel.terminate()


def talk_dim(text: str) -> str:
    return f"\033[2m({text})\033[0m"


if __name__ == "__main__":
    main()
