#!/usr/bin/env python3
"""Persistent Piper-to-RVC voice service with concurrent text generation."""

import base64
import json
import queue
import re
import tempfile
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from piper import PiperVoice
from rvc_python.infer import RVCInference

import alfred
from memory import Memory

ROOT = Path(__file__).parent
PIPER_MODEL = ROOT / "tts-models" / "piper" / "en_GB-alan-medium.onnx"
RVC_DIR = ROOT / "rvc-model"


class VoicePipeline:
    def __init__(self):
        # Piper is only the fast British carrier performance. RVC supplies the
        # final voice, and remains on the GTX 1060.
        self.piper = PiperVoice.load(PIPER_MODEL, use_cuda=False)
        self.rvc = RVCInference(
            device="cuda:0",
            model_path=str(RVC_DIR / "AlfredPennyworth_465e_8835s.pth"),
            index_path=str(RVC_DIR / "AlfredPennyworth.index"),
            version="v2",
        )
        self.rvc.set_params(f0method="rmvpe", index_rate=0.7, protect=0.33)
        self.temp = tempfile.TemporaryDirectory(prefix="alfred-voice-")
        # Force lazy CUDA kernels and RVC feature models to load before the
        # first real request.
        self.create("Ready, sir.")

    def create(self, text: str) -> tuple[bytes, float, float]:
        source = Path(self.temp.name) / "source.wav"
        converted = Path(self.temp.name) / "converted.wav"
        started = time.perf_counter()
        with wave.open(str(source), "wb") as wav_file:
            self.piper.synthesize_wav(text, wav_file)
        tts_finished = time.perf_counter()
        self.rvc.infer_file(str(source), str(converted))
        finished = time.perf_counter()
        return converted.read_bytes(), tts_finished - started, finished - tts_finished


PIPELINE = None
PERSONA = None
MEMORY = None


class SentenceBuffer:
    def __init__(self, emit):
        self.text = ""
        self.emit = emit

    def add(self, piece: str) -> None:
        self.text += piece
        while True:
            boundary = None
            for match in re.finditer(r"[.!?;,:—][\"']?(?=\s)", self.text):
                candidate = self.text[:match.end()]
                terminal = match.group(0)[0] in ".!?"
                if terminal or len(candidate.split()) >= 10:
                    boundary = match.end()
                    break
            if boundary is None:
                words = list(re.finditer(r"\S+\s+", self.text))
                if len(words) >= 14:
                    boundary = words[13].end()
            if boundary is None:
                return
            sentence = self.text[:boundary].strip()
            self.text = self.text[boundary:].lstrip()
            if sentence:
                self.emit(sentence)

    def flush(self) -> None:
        if self.text.strip():
            self.emit(self.text.strip())
            self.text = ""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ready")

    def do_POST(self):
        if self.path == "/chat":
            self.chat()
            return
        if self.path != "/speak":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            text = json.loads(self.rfile.read(length))["text"].strip()
            if not text:
                raise ValueError("text is empty")
            audio, tts_time, rvc_time = PIPELINE.create(text)
            print(f"tts={tts_time:.3f}s rvc={rvc_time:.3f}s chars={len(text)}", flush=True)
        except Exception as exc:
            self.send_error(500, str(exc))
            return
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("X-TTS-Seconds", f"{tts_time:.3f}")
        self.send_header("X-RVC-Seconds", f"{rvc_time:.3f}")
        self.end_headers()
        self.wfile.write(audio)

    def chat(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            prompt = json.loads(self.rfile.read(length))["text"].strip()
            if not prompt:
                raise ValueError("text is empty")
        except Exception as exc:
            self.send_error(400, str(exc))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        work = queue.Queue(maxsize=4)
        worker_error = []

        def convert_sentences() -> None:
            while True:
                sentence = work.get()
                if sentence is None:
                    return
                try:
                    spoken = sentence if sentence[-1] in ".!?;,:—" else sentence + ","
                    audio, tts_time, rvc_time = PIPELINE.create(spoken)
                    frame = {
                        "text": sentence,
                        "audio": base64.b64encode(audio).decode("ascii"),
                        "tts_seconds": tts_time,
                        "rvc_seconds": rvc_time,
                    }
                    self.wfile.write(json.dumps(frame).encode("utf-8") + b"\n")
                    self.wfile.flush()
                except Exception as exc:
                    worker_error.append(exc)
                    return

        worker = threading.Thread(target=convert_sentences, daemon=True)
        worker.start()

        def emit(sentence: str) -> None:
            work.put(sentence)

        history = MEMORY.recent()
        context = MEMORY.context(prompt)
        delivery = "(kept private)"
        context = f"{context}\n{delivery}" if context else delivery
        history.append({"role": "user", "content": prompt})
        sentences = SentenceBuffer(emit)
        try:
            reply = alfred.ask(
                alfred.DEFAULT_MODEL,
                PERSONA,
                history,
                memory_context=context,
                echo=False,
                stats=False,
                on_piece=sentences.add,
            )
            sentences.flush()
            work.put(None)
            worker.join()
            if worker_error:
                raise worker_error[0]
            MEMORY.record(prompt, reply)
            self.wfile.write(b'{"done":true}\n')
            self.wfile.flush()
        except Exception as exc:
            if worker.is_alive():
                work.put(None)
                worker.join()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8") + b"\n")
            self.wfile.flush()

    def log_message(self, format, *args):
        return


def main() -> None:
    global PIPELINE, PERSONA, MEMORY
    alfred.SHOTS = alfred.load_examples()
    PERSONA = alfred.load_persona()
    MEMORY = Memory(alfred.MEMORY_DB)
    PIPELINE = VoicePipeline()
    print("voice service ready on 127.0.0.1:5051", flush=True)
    HTTPServer(("127.0.0.1", 5051), Handler).serve_forever()


if __name__ == "__main__":
    main()
