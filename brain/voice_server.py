#!/usr/bin/env python3
"""Persistent streaming voice service with RVC and direct-Piper modes."""

import base64
import json
import os
import queue
import re
import tempfile
import threading
import time
import urllib.request
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
from piper import PiperVoice
from rvc_python.infer import RVCInference
import soundfile as sf
from scipy.signal import resample_poly

import alfred
import guru
import memory
import media
import memory_tools
import weather
from memory import Memory
import random

ROOT = Path(__file__).resolve().parent.parent   # project root: the models live beside brain/
PIPER_MODEL = Path(os.environ.get(
    "ALFRED_PIPER_MODEL", ROOT / "tts-models" / "piper" / "en_GB-alan-medium.onnx"
))
DIRECT_PIPER = "ALFRED_PIPER_MODEL" in os.environ
RVC_DIR = ROOT / "rvc-model"
OUTPUT_RATE = 32000


class VoicePipeline:
    def __init__(self):
        # Piper is only the fast British carrier performance. RVC supplies the
        # final voice, and remains on the GTX 1060.
        self.piper = PiperVoice.load(PIPER_MODEL, use_cuda=False)
        self.rvc = None
        if not DIRECT_PIPER:
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
        if self.rvc is None:
            samples, rate = sf.read(source, dtype="float32")
            if rate != OUTPUT_RATE:
                divisor = np.gcd(rate, OUTPUT_RATE)
                samples = resample_poly(samples, OUTPUT_RATE // divisor, rate // divisor)
            sf.write(converted, samples, OUTPUT_RATE, subtype="PCM_16")
        else:
            self.rvc.infer_file(str(source), str(converted))
        finished = time.perf_counter()
        return converted.read_bytes(), tts_finished - started, finished - tts_finished


PIPELINE = None
PERSONA = None
MEMORY = None
# The last YouTube results and which of them is playing, so "the second one"
# and "next" mean something. One household, one list.
MEDIA_RESULTS: list = []
MEDIA_POSITION = [-1]
# The last commentator section talked about, so "play that part" can follow it.
GURU_LAST: list = []

# Nothing may touch either GPU while a question is in flight.
BUSY = threading.Lock()
# Warm once at start, then only after this long with nothing asked. It used to
# run every 40s regardless, holding BUSY for 0.4-1.4s each time, so a question
# landing in that window simply waited. Measured 2026-09-16 with the loop off:
# after 3 and 10 minutes idle the decider, the answer's first token, the embedder
# and Piper were all exactly as fast as hot (keep_alive=-1 and two llama.cpp
# slots mean the cached prompts are never evicted). Only a restart loses them.
KEEP_WARM_SECONDS = 600
LAST_ACTIVITY = float("-inf")  # monotonic time of the last turn or warmup; -inf so start-up always warms


def mark_activity() -> None:
    global LAST_ACTIVITY
    LAST_ACTIVITY = time.monotonic()


def keep_warm() -> None:
    """Hold the model's prefix and both cards at temperature between questions.

    Ollama only reuses the prefix it shares with the request immediately before,
    and in real use every question carries a different memory context, so that
    prefix is constantly being lost. This sends the persona and the examples —
    exactly the prefix `alfred.ask` puts in front of every request — so the
    evaluation of those ~2400 tokens is already done when a question arrives.

    This is worth nothing on its own. It only pays off because `ask` keeps the
    persona and shots contiguous at the front; warming a prefix the real request
    does not share measured identical to no warmup at all. Over eight realistic
    turns the pair took mean prompt evaluation from 0.43s to 0.22s and the worst
    case from 1.49s to 0.37s.

    One token is generated and thrown away. Nothing is recorded to memory.
    """
    payload = {
        "model": alfred.DEFAULT_MODEL,
        "keep_alive": -1,
        "messages": [{"role": "system", "content": PERSONA}] + alfred.SHOTS,
        "stream": False,
        "think": False,
        "options": {"num_predict": 1},
    }
    body = json.dumps(payload).encode("utf-8")
    # The decider's prompt is the other prefix every question pays for. With
    # OLLAMA_NUM_PARALLEL=2 it lives in its own llama.cpp slot instead of
    # evicting the persona, which took a decider call from 1.1s to 0.5s — but
    # only once that slot holds it. Cold, the first decider of the day is 1.6s.
    decider_body = json.dumps({
        "model": alfred.DEFAULT_MODEL,
        "keep_alive": -1,
        "messages": [{"role": "system", "content": memory_tools.DECIDER_SYSTEM}],
        "tools": memory_tools.TOOLS,
        "stream": False,
        "think": False,
        "options": {"num_predict": 1},
    }).encode("utf-8")
    global LAST_ACTIVITY
    while True:
        if time.monotonic() - LAST_ACTIVITY < KEEP_WARM_SECONDS:
            time.sleep(5.0)
            continue          # something ran recently; everything is still warm
        if not BUSY.acquire(blocking=False):
            time.sleep(1.0)
            continue          # a real question is being answered; it is warm
        try:
            request = urllib.request.Request(
                f"{alfred.SERVER}/api/chat", data=body,
                headers={"Content-Type": "application/json"},
            )
            started = time.perf_counter()
            with urllib.request.urlopen(request, timeout=30) as response:
                detail = json.loads(response.read())
            decider = urllib.request.Request(
                f"{alfred.SERVER}/api/chat", data=decider_body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(decider, timeout=30) as response:
                response.read()
            # Ollama juggles two models on one card and evicted the embedder
            # overnight, so the first memory search of the day paid a 2.8s load.
            # Same argument as everything else here: the first question after a
            # quiet spell is the one that must not feel slow.
            memory._embed(["keep warm"])
            PIPELINE.create("Mm.")
            print(
                f"warm {time.perf_counter() - started:.2f}s "
                f"prefill={detail.get('prompt_eval_count')} tok in "
                f"{detail.get('prompt_eval_duration', 0) / 1e9:.2f}s",
                flush=True,
            )
        except Exception as exc:
            # A failed warmup must never take the service down, but a silently
            # failing one is worse than none — it looks like it is working.
            print(f"warm failed: {exc}", flush=True)
        finally:
            LAST_ACTIVITY = time.monotonic()
            BUSY.release()



# Short enough that the search is usually still running when he finishes saying
# it, which is the point — he should not be waiting on his own courtesy.
HOLDING_LINES = (
    "One moment, sir.",
    "Let me look, sir.",
    "A moment.",
    "Checking, sir.",
)

class SentenceBuffer:
    """Cut the stream into whole sentences and nothing smaller.

    The previous version also broke at commas past ten words, and failed that
    at a hard fourteen-word count with no punctuation involved at all. That cut
    clauses in half ("...to give" / "it a better grip"), orphaned "sir." into an
    utterance of its own, and — because any chunk not ending in punctuation had
    a comma appended — made Piper sing a rising continuation and then stop dead.
    Every one of those is audible as a seam.

    A complete sentence is the smallest unit Piper can give a correct intonation
    contour to, so it is the smallest unit worth sending.
    """

    TERMINAL = re.compile(r"[.!?][\"')\]]?(?=\s)")
    CLAUSE = re.compile(r"[,;:—](?=\s)")
    # Only used to break a sentence that has run away without any stop at all.
    MAX_WORDS = 30
    # A period after one of these is not the end of a sentence.
    ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "st", "vs", "e.g", "i.e", "approx", "fig", "no"}

    def __init__(self, emit):
        self.text = ""
        self.emit = emit

    def _is_abbreviation(self, end: int) -> bool:
        word = re.search(r"(\S+)\.$", self.text[:end])
        return bool(word) and word.group(1).lower() in self.ABBREVIATIONS

    def _boundary(self) -> int | None:
        for match in self.TERMINAL.finditer(self.text):
            if not self._is_abbreviation(match.end()):
                return match.end()
        if len(self.text.split()) <= self.MAX_WORDS:
            return None
        # Runaway sentence. Fall back to the last real clause break, so the seam
        # at least lands where a speaker would have drawn breath. Never invent
        # one where the text has none.
        clauses = list(self.CLAUSE.finditer(self.text))
        return clauses[-1].end() if clauses else None

    def add(self, piece: str) -> None:
        self.text += piece
        while True:
            boundary = self._boundary()
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
            with BUSY:
                audio, tts_time, rvc_time = PIPELINE.create(text)
                mark_activity()
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

        # Held for the whole turn so the warmup cannot contend for either card
        # in the middle of an answer.
        BUSY.acquire()
        work = queue.Queue(maxsize=4)
        worker_error = []

        def convert_sentences() -> None:
            while True:
                sentence = work.get()
                if sentence is None:
                    return
                if isinstance(sentence, dict):
                    # Not speech: an instruction for the client, such as a video
                    # to play, kept in order with the sentences around it.
                    try:
                        self.wfile.write(json.dumps(sentence).encode("utf-8") + b"\n")
                        self.wfile.flush()
                    except Exception as exc:
                        worker_error.append(exc)
                        return
                    continue
                try:
                    audio, tts_time, rvc_time = PIPELINE.create(sentence)
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
        bare_prompt = " ".join(re.findall(r"[^\W_]+", prompt.lower()))
        direct_reply = None
        if bare_prompt in {
            "what time is it", "what is the time", "whats the time",
            "tell me the time", "current time", "time please",
        }:
            direct_reply = memory.local_time_reply()
        # Pass one decides what to look up, with no persona and no examples in
        # front of it. Pass two — the one below, which actually answers — never
        # sees a tool definition. If the decider fails for any reason we fall
        # back to blind retrieval, which is what every turn did before this.
        # Said aloud the instant a search starts, so the wait has a voice in
        # front of it instead of six seconds of nothing. Rotated because a
        # butler who says the identical four words every time is a doorbell.
        def announce() -> None:
            emit(random.choice(HOLDING_LINES))

        # The weather comes from a forecast service, never from the web search:
        # search snippets said 78 on a 92-degree afternoon. A forecast turn also
        # skips the decider, so it is quicker than any other looked-up turn. If
        # the service fails, or no home location is set, the turn carries on
        # exactly as it did before.
        # "Play…" is a command, not a question: found, announced in a fixed line
        # and handed to the client, without the decider or the model. "Find
        # videos of…" is looked up here and then answered by the model as usual,
        # so he can read the results out; "the second one" plays from them.
        forecast = None
        videos = None
        play = None
        commentary = None
        # A commentator's take, from his own videos: summarised for "what does
        # the guru think", or the section itself played for "play the guru's
        # breakdown of…". Checked before media.parse, which would otherwise read
        # "play the guru's breakdown of x" as a YouTube search for those words.
        guru_request = None if direct_reply is not None else guru.parse(prompt, bool(GURU_LAST))
        if guru_request is not None:
            try:
                if guru_request["action"] == "play_last":
                    play = GURU_LAST[0]
                    direct_reply = "Here it is, sir."
                else:
                    if guru_request["action"] == "ask":
                        announce()
                    found = guru.find_section(guru_request)
                    if found is None:
                        direct_reply = "I can't find him talking about that."
                    else:
                        GURU_LAST[:] = [guru.clip(found)]
                        if guru_request["action"] == "play":
                            play = GURU_LAST[0]
                            section = found["section"]
                            direct_reply = (f"{found['commentator']} on {section['title']}, sir." if section
                                            else f"{found['commentator']}'s latest, sir.")
                        else:
                            commentary = guru.context(found, guru_request.get("subject") or "")
            except Exception as exc:
                print(f"guru failed: {exc}", flush=True)
                direct_reply = "I can't reach his videos just now."
            print(f"memory guru {guru_request['action']}", flush=True)
        media_request = (None if direct_reply is not None or commentary is not None
                         else media.parse(prompt, bool(MEDIA_RESULTS)))
        if media_request is not None:
            kind, value = media_request
            try:
                if kind in ("play", "search"):
                    results = media.search(value)
                    if not results:
                        direct_reply = "I couldn't find anything by that name."
                    elif kind == "play":
                        MEDIA_RESULTS[:] = results
                        play = media.best(results)
                    else:
                        MEDIA_RESULTS[:] = results
                        MEDIA_POSITION[0] = -1
                        videos = media.results_context(value, results)
                elif kind == "pick":
                    index = value - 1 if value > 0 else len(MEDIA_RESULTS) - 1
                    if 0 <= index < len(MEDIA_RESULTS):
                        play = MEDIA_RESULTS[index]
                    else:
                        direct_reply = f"There were only {len(MEDIA_RESULTS)}, sir."
                elif kind == "next":
                    index = MEDIA_POSITION[0] + 1
                    if index < len(MEDIA_RESULTS):
                        play = MEDIA_RESULTS[index]
                    else:
                        direct_reply = "That was the last of them."
            except Exception as exc:
                print(f"media failed: {exc}", flush=True)
                direct_reply = "I can't reach YouTube just now."
            if play is not None and guru_request is None:
                MEDIA_POSITION[0] = MEDIA_RESULTS.index(play) if play in MEDIA_RESULTS else 0
                direct_reply = media.announce(play)
            print(f"memory media {kind}{'' if direct_reply or videos else ' FAILED'}", flush=True)
        if (direct_reply is None and videos is None and commentary is None
                and weather.asks_about_weather(prompt, history)):
            forecast = weather.lookup(prompt, history)
        if videos is not None or commentary is not None:
            consulted = {"context": memory_tools._render(MEMORY, [], []),
                         "calls": [], "failed": False}
        elif forecast is not None:
            print("memory weather", flush=True)
            consulted = {"context": memory_tools._render(MEMORY, [], []),
                         "calls": [], "failed": False}
        elif direct_reply is not None or not memory_tools.may_need_tools(prompt):
            consulted = {"context": memory_tools._render(MEMORY, [], []),
                         "calls": [], "failed": False}
        else:
            # Tried starting the answer alongside the decider, on the bet it would
            # call nothing (2026-09-16). The MI50 does not run two requests for
            # free: the decider slowed under the load, so no-tool turns gained
            # 0.23s while memory turns lost 0.96s and web turns 1.33s before the
            # holding line. The two stay in series.
            consulted = memory_tools.consult(MEMORY, prompt, alfred.DEFAULT_MODEL,
                                             alfred.SERVER, on_search=announce,
                                             history=history)
        context = consulted["context"] if not consulted["failed"] else MEMORY.context(prompt)
        if consulted["calls"]:
            print("memory " + ", ".join(
                f"{call['tool']}{'' if call['ok'] else ' FAILED'}" for call in consulted["calls"]
            ), flush=True)
        if forecast:
            context = f"{context}\n{forecast}" if context else forecast
        if videos:
            context = f"{context}\n{videos}" if context else videos
        if commentary:
            context = f"{context}\n{commentary}" if context else commentary
        delivery = alfred.SPOKEN_DELIVERY
        context = f"{context}\n{delivery}" if context else delivery
        history.append({"role": "user", "content": prompt})
        sentences = SentenceBuffer(emit)
        try:
            if direct_reply is not None:
                reply = direct_reply
                sentences.add(reply)
            else:
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
            if play is not None:
                work.put({"media": {key: play.get(key) for key in ("id", "title", "channel", "duration", "start", "end")
                                    if play.get(key) is not None}})
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
        finally:
            mark_activity()
            BUSY.release()

    def log_message(self, format, *args):
        return


def main() -> None:
    global PIPELINE, PERSONA, MEMORY
    alfred.SHOTS = alfred.load_examples()
    PERSONA = alfred.load_persona()
    MEMORY = Memory(alfred.MEMORY_DB)
    PIPELINE = VoicePipeline()
    threading.Thread(target=keep_warm, daemon=True).start()
    # A second copy on another port, with ALFRED_MEMORY_DB pointed at a scratch
    # database, is how test turns run without stopping the real one.
    port = int(os.environ.get("ALFRED_VOICE_PORT", "5051"))
    print(f"voice service ready on 127.0.0.1:{port}", flush=True)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
