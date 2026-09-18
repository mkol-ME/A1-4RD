#!/usr/bin/env python3
"""Persistent Whisper service on the GTX 1060.

`whisper_transcribe.py` loads the model on every invocation, which is fine for
a file and useless for ears — the load alone costs more than most utterances
last. This keeps it resident, the same reasoning as the voice service and
OLLAMA_KEEP_ALIVE=-1.

It lives in its own process and its own venv on purpose. The RVC environment is
pinned hard around fairseq and torch, and faster-whisper brings its own
ctranslate2; putting them in one interpreter is asking for a dependency fight
over something that only needs a socket between them.
"""

import base64
import io
import json
import os
import time
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from faster_whisper import WhisperModel, decode_audio

import audio_archive
import prompts

# The client says which language it is listening in: "en" (the default) or "pt".
#
# English mode is the English-only model, exactly as it always was. Portuguese
# mode uses the multilingual model, choosing between Portuguese and English on
# each turn so that "speak English" still comes through as English.
#
# Guessing the language on every turn was tried first (2026-09-17): English
# first, and a multilingual second pass when the English model scored its own
# tokens badly. It caught 32/32 Portuguese test clips, but in real use switching
# back and forth was unreliable, and the owner asked for an explicit command.
MODEL = "small.en"
MULTILINGUAL_MODEL = "small"
MODES = ("en", "pt")
# The 1060 is Pascal — no tensor cores and crippled FP16, so int8_float32 is the
# right compute type here and float16 would be slower, not faster.
COMPUTE = "int8_float32"
PORT = 5052
MAX_AUDIO_BYTES = 32 * 1024 * 1024
# Every utterance is kept, with the transcript that was used for it, so a better
# Whisper can be run over it later and a voice can be learned from it. The client
# sends the finished clip here once, after the partial ones it races through
# /transcribe, so what is stored is one clip per thing said.
ARCHIVE = None

# Whisper has never met most of these words and guesses at them phonetically —
# "Bambu P1S" came back as "Bamboo P1's". Priming it with the vocabulary this
# desk actually uses costs nothing per utterance and fixes the proper nouns that
# matter most, since they are exactly the words a command depends on.
# Local place names earn their spot the same way: the home city and school came
# back as three different near-misses in 3 of 12 clips, and with them listed, 12
# of 12 (2026-09-16, 88 synthetic clips, error rate 7.0% -> 6.4%, no cost in
# time). They are personal, so they live in persona/vocabulary.local.txt, which
# git ignores, rather than here. Skipping timestamps (-26ms) and the VAD (-5ms)
# were measured too and not taken: both added errors, and the VAD is what keeps
# a keyboard click from being transcribed as a sentence.
# His name and the owner's lead the list. The owner's is private, so it comes
# from persona/prompts.json with the rest of his wording.
NAMES = f"Alfred. {prompts.OWNER}."
VOCABULARY = (
    f"{NAMES} Bambu P1S, PETG, ABS, PLA, TPU, filament, nozzle, extruder, "
    "retraction, brim, raft, first layer, bed adhesion, warping, gcode, slicer, "
    "Klipper, Marlin, infill, elephant foot, Ollama, Qwen, git, commit, repository."
)
LOCAL_VOCABULARY = prompts.PERSONA_DIR / "vocabulary.local.txt"
if LOCAL_VOCABULARY.exists():
    VOCABULARY += " " + " ".join(LOCAL_VOCABULARY.read_text(encoding="utf-8").split())
# The people he talks about, in both languages. In the first Portuguese session
# "o Diego" came back as "o chão", so "never forget this, Diego is..." had
# nothing to save and "do you know Diego" nothing to find. Over ten synthetic
# Portuguese clips (2026-09-17) the name fixed "o tirágua é o quê", settled
# "Tiago" into one spelling, and left "o chão está molhado" alone. Friends'
# names are personal, so they live in persona/people.local.txt, one per line.
LOCAL_PEOPLE = prompts.PERSONA_DIR / "people.local.txt"
PEOPLE = NAMES
if LOCAL_PEOPLE.exists():
    PEOPLE += " " + " ".join(f"{name.strip()}." for name in LOCAL_PEOPLE.read_text(encoding="utf-8").splitlines()
                             if name.strip())
VOCABULARY = PEOPLE + VOCABULARY.removeprefix(NAMES)
# Portuguese gets names only. With the printing terms too, "toca Bohemian
# Rhapsody" came back as "toca a Bambu P1S": the prompt leaked into the words.
PROMPTS = {"en": VOCABULARY, "pt": PEOPLE}


class Ears:
    def __init__(self):
        self.model = WhisperModel(MODEL, device="cuda", compute_type=COMPUTE)
        # Both stay loaded (about 0.43 GB each on the 1060's 6 GB), so a
        # Portuguese turn never waits for a model to load.
        self.multilingual = WhisperModel(MULTILINGUAL_MODEL, device="cuda", compute_type=COMPUTE)
        # Force the CUDA kernels and the encoder to load before anyone speaks.
        silence = io.BytesIO()
        with wave.open(silence, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(b"\x00\x00" * 16000)
        silence.seek(0)
        self.transcribe(silence.read())

    def transcribe(self, audio: bytes, mode: str = "en") -> tuple[str, float, str]:
        started = time.perf_counter()
        samples = decode_audio(io.BytesIO(audio), sampling_rate=16000)
        if mode != "pt":
            text, _ = self._pass(self.model, samples, "en")
            return text, time.perf_counter() - started, "en"
        _, _, probabilities = self.multilingual.detect_language(samples)
        probabilities = dict(probabilities)
        language = max(MODES, key=lambda code: probabilities.get(code, 0.0))
        text, _ = self._pass(self.multilingual, samples, language)
        return text, time.perf_counter() - started, language

    def _pass(self, model, samples, language: str) -> tuple[str, float]:
        """Text, and the average log-probability of its tokens (how sure the model was)."""
        segments = list(model.transcribe(
            samples,
            language=language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,   # stops it inventing continuations
            initial_prompt=PROMPTS.get(language),
        )[0])
        tokens = sum(len(segment.tokens) for segment in segments)
        confidence = (sum(segment.avg_logprob * len(segment.tokens) for segment in segments) / tokens
                      if tokens else 0.0)
        return " ".join(segment.text.strip() for segment in segments).strip(), confidence


EARS = None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ready")

    def do_POST(self):
        path, _, query = self.path.partition("?")
        if path not in ("/transcribe", "/keep"):
            self.send_error(404)
            return
        if path == "/keep":
            self.keep()
            return
        mode = "pt" if "mode=pt" in query.split("&") else "en"
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_AUDIO_BYTES:
                raise ValueError(f"audio must be 1..{MAX_AUDIO_BYTES} bytes, got {length}")
            audio = self.rfile.read(length)
            text, elapsed, language = EARS.transcribe(audio, mode)
        except Exception as exc:
            self.send_error(500, str(exc))
            return
        body = json.dumps({"text": text, "seconds": round(elapsed, 3), "language": language}).encode("utf-8")
        print(f"heard {elapsed:.2f}s [{language}] {text!r}", flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def keep(self):
        """Archive one finished clip and the transcript that was used for it."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_AUDIO_BYTES * 2:
                raise ValueError(f"body must be 1..{MAX_AUDIO_BYTES * 2} bytes, got {length}")
            body = json.loads(self.rfile.read(length))
            saved = ARCHIVE.keep(base64.b64decode(body["audio"]), body.get("text", ""),
                                 body.get("language", "en"), body.get("source", "voice"))
        except Exception as exc:
            self.send_error(500, str(exc))
            return
        payload = json.dumps({"kept": saved is not None}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


def main() -> None:
    global EARS, ARCHIVE
    EARS = Ears()
    ARCHIVE = audio_archive.Archive()
    print(f"archive: {ARCHIVE.stats()}", flush=True)
    print(f"whisper service ready on 127.0.0.1:{PORT} ({MODEL} for English, {MULTILINGUAL_MODEL} for "
          f"Portuguese mode, {COMPUTE})", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
