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

import io
import json
import time
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from faster_whisper import WhisperModel

MODEL = "small.en"
# The 1060 is Pascal — no tensor cores and crippled FP16, so int8_float32 is the
# right compute type here and float16 would be slower, not faster.
COMPUTE = "int8_float32"
PORT = 5052
MAX_AUDIO_BYTES = 32 * 1024 * 1024

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
VOCABULARY = (
    "Alfred. the user. Bambu P1S, PETG, ABS, PLA, TPU, filament, nozzle, extruder, "
    "retraction, brim, raft, first layer, bed adhesion, warping, gcode, slicer, "
    "Klipper, Marlin, infill, elephant foot, Ollama, Qwen, git, commit, repository."
)
LOCAL_VOCABULARY = Path(__file__).resolve().parent.parent / "persona" / "vocabulary.local.txt"
if LOCAL_VOCABULARY.exists():
    VOCABULARY += " " + " ".join(LOCAL_VOCABULARY.read_text(encoding="utf-8").split())


class Ears:
    def __init__(self):
        self.model = WhisperModel(MODEL, device="cuda", compute_type=COMPUTE)
        # Force the CUDA kernels and the encoder to load before anyone speaks.
        silence = io.BytesIO()
        with wave.open(silence, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(b"\x00\x00" * 16000)
        silence.seek(0)
        self.transcribe(silence.read())

    def transcribe(self, audio: bytes) -> tuple[str, float]:
        started = time.perf_counter()
        segments, _ = self.model.transcribe(
            io.BytesIO(audio),
            language="en",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,   # stops it inventing continuations
            initial_prompt=VOCABULARY,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text, time.perf_counter() - started


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
        if self.path != "/transcribe":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_AUDIO_BYTES:
                raise ValueError(f"audio must be 1..{MAX_AUDIO_BYTES} bytes, got {length}")
            audio = self.rfile.read(length)
            text, elapsed = EARS.transcribe(audio)
        except Exception as exc:
            self.send_error(500, str(exc))
            return
        body = json.dumps({"text": text, "seconds": round(elapsed, 3)}).encode("utf-8")
        print(f"heard {elapsed:.2f}s {text!r}", flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main() -> None:
    global EARS
    EARS = Ears()
    print(f"whisper service ready on 127.0.0.1:{PORT} ({MODEL}, {COMPUTE})", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
