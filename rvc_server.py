#!/usr/bin/env python3
"""Persistent RVC conversion service, intended for GPU 1."""

import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from rvc_python.infer import RVCInference

ROOT = Path(__file__).parent
RVC_DIR = ROOT / "rvc-model"


class Pipeline:
    def __init__(self):
        self.rvc = RVCInference(device="cuda:0", model_path=str(RVC_DIR / "AlfredPennyworth_465e_8835s.pth"), index_path=str(RVC_DIR / "AlfredPennyworth.index"), version="v2")
        self.rvc.set_params(f0method="rmvpe", index_rate=0.7, protect=0.33)
        self.temp = tempfile.TemporaryDirectory(prefix="alfred-rvc-")

    def convert(self, source_audio: bytes) -> tuple[bytes, float]:
        source = Path(self.temp.name) / "source.wav"
        output = Path(self.temp.name) / "converted.wav"
        source.write_bytes(source_audio)
        started = time.perf_counter()
        self.rvc.infer_file(str(source), str(output))
        return output.read_bytes(), time.perf_counter() - started


PIPELINE = None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200); self.end_headers(); self.wfile.write(b"ready")

    def do_POST(self):
        if self.path != "/convert":
            self.send_error(404)
            return
        try:
            audio = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            converted, elapsed = PIPELINE.convert(audio)
        except Exception as exc:
            self.send_error(500, str(exc)); return
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(converted)))
        self.send_header("X-RVC-Seconds", f"{elapsed:.3f}")
        self.end_headers(); self.wfile.write(converted)

    def log_message(self, format, *args):
        return


def main() -> None:
    global PIPELINE
    PIPELINE = Pipeline()
    print("RVC service ready on 127.0.0.1:5051", flush=True)
    HTTPServer(("127.0.0.1", 5051), Handler).serve_forever()


if __name__ == "__main__":
    main()
