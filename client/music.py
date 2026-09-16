"""Music through Alfred's speaker: the stream from the media service, and its controls.

The server decodes, so this only plays raw 48 kHz stereo PCM — the same job a
Pi Zero will do later. Controls are decided here rather than on the server:
"pause" has to work instantly and while the music is loud, and none of them
needs the model.
"""

import re
import threading
import time
import urllib.request

import numpy as np
import sounddevice as sd

MEDIA_URL = "http://127.0.0.1:5053"
RATE = 48000
CHANNELS = 2
CHUNK_BYTES = 4800 * CHANNELS * 2        # 100 ms
DEFAULT_VOLUME = 0.5
VOLUME_STEP = 1.5                        # louder/quieter multiply or divide by this
DUCKED = 0.15                            # while he talks, or is being spoken to

CONTROLS = {
    "pause": ("pause", "pause it", "pause the music", "pause this", "pause the song", "hold on", "wait"),
    "resume": ("resume", "unpause", "continue", "keep playing", "carry on", "play", "resume the music",
               "start it again", "back on"),
    "stop": ("stop", "stop it", "stop the music", "stop playing", "turn it off", "shut it off",
             "kill the music", "enough music", "stop the song", "that's enough", "thats enough"),
    "louder": ("louder", "turn it up", "volume up", "a bit louder", "turn up the volume", "crank it",
               "turn the music up", "up"),
    "quieter": ("quieter", "softer", "turn it down", "volume down", "a bit quieter", "lower the volume",
                "turn down the volume", "turn the music down", "down"),
}
_LOOKUP = {phrase: action for action, phrases in CONTROLS.items() for phrase in phrases}


def control(prompt: str) -> str | None:
    """pause, resume, stop, louder, quieter — or None if this is not a music control."""
    text = " ".join(re.findall(r"[a-z']+", prompt.lower()))
    text = re.sub(r"^(?:please |can you |could you |okay |ok |hey )+", "", text)
    text = re.sub(r"(?: please| for me| a bit| a little)+$", "", text)
    return _LOOKUP.get(text)


def open_output() -> sd.OutputStream:
    """WASAPI where available, as for his voice (lower latency), else the default device."""
    try:
        wasapi = next(api for api in sd.query_hostapis() if "WASAPI" in api["name"])
        if wasapi["default_output_device"] >= 0:
            return sd.OutputStream(
                device=wasapi["default_output_device"], samplerate=RATE, channels=CHANNELS,
                dtype="float32", extra_settings=sd.WasapiSettings(auto_convert=True))
    except (StopIteration, sd.PortAudioError, AttributeError, ValueError):
        pass
    return sd.OutputStream(samplerate=RATE, channels=CHANNELS, dtype="float32")


class MusicPlayer:
    def __init__(self, media_url: str = MEDIA_URL, opener=None, output=None):
        self.media_url = media_url
        self.opener = opener or (lambda url: urllib.request.urlopen(url, timeout=30))
        self.output = output or open_output
        self.volume = DEFAULT_VOLUME
        self.title = None
        self._ducks = 0
        self._paused = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        """Playing or paused: music is the thing in the room."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def paused(self) -> bool:
        return self.active and self._paused.is_set()

    def play(self, info: dict) -> None:
        self.stop()
        with self._lock:
            self._stop = threading.Event()
            self._paused.clear()
            self.title = info.get("title")
            self._thread = threading.Thread(target=self._run, args=(info["id"], self._stop), daemon=True)
            self._thread.start()

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def stop(self) -> None:
        with self._lock:
            thread, self._thread = self._thread, None
            self._stop.set()
        if thread is not None:
            thread.join(timeout=3)
        self.title = None

    def louder(self) -> None:
        self.volume = min(1.0, self.volume * VOLUME_STEP)

    def quieter(self) -> None:
        self.volume = max(0.02, self.volume / VOLUME_STEP)

    def apply(self, action: str) -> None:
        getattr(self, action)()

    def duck(self) -> None:
        """Lower the music while he talks or is being addressed. Nests."""
        self._ducks += 1

    def unduck(self) -> None:
        self._ducks = max(0, self._ducks - 1)

    def gain(self) -> float:
        return self.volume * (DUCKED if self._ducks else 1.0)

    def _run(self, video_id: str, stop: threading.Event) -> None:
        response = stream = None
        try:
            response = self.opener(f"{self.media_url}/stream?id={video_id}")
            stream = self.output()
            stream.start()
            leftover = b""
            current = self.gain()
            while not stop.is_set():
                if self._paused.is_set():
                    time.sleep(0.05)     # not reading: the server's decoder waits on us
                    continue
                data = leftover + response.read(CHUNK_BYTES)
                if len(data) <= len(leftover):
                    break                # end of the video
                usable = len(data) - len(data) % (CHANNELS * 2)
                data, leftover = data[:usable], data[usable:]
                block = np.frombuffer(data, dtype="<i2").astype(np.float32).reshape(-1, CHANNELS) / 32768.0
                # Ramp between gains across the block, so ducking does not click.
                target = self.gain()
                ramp = np.linspace(current, target, block.shape[0], dtype=np.float32)[:, None]
                current = target
                stream.write(block * ramp)
        except Exception as exc:
            print(f"  music stopped: {exc}")
        finally:
            if stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
