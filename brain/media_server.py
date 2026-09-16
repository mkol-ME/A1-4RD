#!/usr/bin/env python3
"""YouTube search and audio, for playing music through Alfred's speaker.

Runs in its own environment (.venv-media: yt-dlp and PyAV, which carries its
own ffmpeg) so the voice server's pinned packages are never touched, and stays
resident so nobody pays yt-dlp's import on every request.

    GET /health
    GET /search?q=bohemian+rhapsody&n=5   -> {"results": [{id, title, channel, duration}]}
    GET /stream?id=<11-char video id>     -> raw PCM, 48 kHz stereo signed 16-bit little-endian

Audio is decoded here rather than on the client because the client is meant to
become a Pi Zero: raw PCM is about 1.5 Mbit/s, trivial on the LAN or Tailscale,
and costs the Pi nothing to play. Measured on the box (2026-09-16): search
1.74s, resolving the stream 1.74s, first decoded audio 0.17s after that.

Localhost only, like every other service here; the laptop reaches it through
the SSH tunnel.
"""

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import av
import yt_dlp

PORT = int(os.environ.get("ALFRED_MEDIA_PORT", "5053"))
RATE = 48000
CHUNK_FRAMES = 4800                     # 100 ms per write
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

# yt-dlp needs a JavaScript runtime to read YouTube's player. Deno is installed
# per user in ~/.deno/bin, which a systemd service does not have on its PATH.
os.environ["PATH"] = os.path.expanduser("~/.deno/bin") + os.pathsep + os.environ.get("PATH", "")

QUIET = {"quiet": True, "no_warnings": True, "noprogress": True}


def search(query: str, count: int = 5) -> list[dict]:
    options = dict(QUIET, extract_flat="in_playlist", skip_download=True)
    with yt_dlp.YoutubeDL(options) as ydl:
        found = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
    results = []
    for entry in found.get("entries") or []:
        if not entry or not VIDEO_ID.match(entry.get("id") or ""):
            continue
        results.append({
            "id": entry["id"],
            "title": entry.get("title") or "",
            "channel": entry.get("channel") or entry.get("uploader") or "",
            "duration": entry.get("duration"),     # None for live streams
        })
    return results


def audio_url(video_id: str) -> str:
    options = dict(QUIET, format="bestaudio/best")
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    return info["url"]


def pcm(video_id: str):
    """Yield the video's audio as 48 kHz stereo s16le bytes, as it decodes."""
    container = av.open(audio_url(video_id), options={
        "reconnect": "1", "reconnect_streamed": "1", "reconnect_delay_max": "5"})
    try:
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="s16", layout="stereo", rate=RATE)
        pending = bytearray()
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                pending += bytes(out.planes[0])[:out.samples * 4]
            while len(pending) >= CHUNK_FRAMES * 4:
                yield bytes(pending[:CHUNK_FRAMES * 4])
                del pending[:CHUNK_FRAMES * 4]
        for out in resampler.resample(None):
            pending += bytes(out.planes[0])[:out.samples * 4]
        if pending:
            yield bytes(pending)
    finally:
        container.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        try:
            if url.path == "/health":
                return self._json({"ok": True})
            if url.path == "/search":
                text = " ".join((query.get("q") or [""])[0].split())[:200]
                if not text:
                    return self._json({"error": "q is required"}, 400)
                count = max(1, min(10, int((query.get("n") or ["5"])[0])))
                return self._json({"results": search(text, count)})
            if url.path == "/stream":
                video_id = (query.get("id") or [""])[0]
                if not VIDEO_ID.match(video_id):
                    return self._json({"error": "bad video id"}, 400)
                return self._stream(video_id)
            return self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            try:
                self._json({"error": f"{type(exc).__name__}: {exc}"}, 502)
            except Exception:
                pass

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _stream(self, video_id: str) -> None:
        chunks = pcm(video_id)
        first = next(chunks)            # resolve before promising a 200
        self.send_response(200)
        self.send_header("Content-Type", f"audio/L16;rate={RATE};channels=2")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            for chunk in [first] if first else []:
                self._chunk(chunk)
            for chunk in chunks:
                # A paused client stops reading; TCP backpressure then parks
                # this loop (and the decoder) until it reads again.
                self._chunk(chunk)
            self.wfile.write(b"0\r\n\r\n")
        finally:
            chunks.close()          # a stopped client ends the decode, not just the send

    def _chunk(self, data: bytes) -> None:
        self.wfile.write(f"{len(data):X}\r\n".encode("ascii") + data + b"\r\n")

    def log_message(self, format, *args):
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    print(f"media service ready on 127.0.0.1:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
