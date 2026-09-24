"""Music through Alfred's speaker: the stream from the media service, and its controls.

Spotify is the other source: it plays in the owner's own Spotify app, and
SpotifyRemote passes the same controls to the voice server, which tells Spotify.
Jukebox puts the two behind one face so the listening loop needs no idea which
is on.

The server decodes, so this only plays raw 48 kHz stereo PCM — the same job a
Pi Zero will do later. Controls are decided here rather than on the server:
"pause" has to work instantly and while the music is loud, and none of them
needs the model.
"""

import json
import re
import threading
import unicodedata
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

# English and Brazilian Portuguese; matched on accent-stripped text.
CONTROLS = {
    "pause": ("pause", "pause it", "pause the music", "pause this", "pause the song", "hold on", "wait",
              "pausa", "pausar", "pausa a musica", "espera"),
    "resume": ("resume", "unpause", "continue", "keep playing", "carry on", "play", "resume the music",
               "start it again", "back on", "continua", "continuar", "volta a tocar", "pode continuar"),
    "stop": ("stop", "stop it", "stop the music", "stop playing", "turn it off", "shut it off",
             "kill the music", "enough music", "stop the song", "that's enough", "thats enough",
             "para", "parar", "para a musica", "desliga", "desliga a musica", "chega"),
    "louder": ("louder", "turn it up", "volume up", "a bit louder", "turn up the volume", "crank it",
               "turn the music up", "up", "mais alto", "aumenta", "aumenta o volume", "sobe o volume"),
    "quieter": ("quieter", "softer", "turn it down", "volume down", "a bit quieter", "lower the volume",
                "turn down the volume", "turn the music down", "down", "mais baixo", "abaixa",
                "abaixa o volume", "diminui o volume"),
}
_LOOKUP = {phrase: action for action, phrases in CONTROLS.items() for phrase in phrases}
# Only Spotify can do these; over a YouTube video "next" means the next search result,
# which the server keeps, so they are not intercepted then.
SPOTIFY_CONTROLS = {
    "next": ("next", "skip", "skip it", "skip this", "skip this one", "skip this song", "next song",
             "next track", "next one", "proxima", "pula", "pula essa", "proxima musica"),
    "previous": ("previous", "go back", "back", "last song", "previous song", "play the last one",
                 "the one before", "anterior", "volta", "musica anterior"),
}
_SPOTIFY_LOOKUP = {phrase: action for action, phrases in SPOTIFY_CONTROLS.items() for phrase in phrases}


def _control_text(prompt: str) -> str:
    text = unicodedata.normalize("NFKD", prompt.lower()).encode("ascii", "ignore").decode()
    text = " ".join(re.findall(r"[a-z']+", text))
    text = re.sub(r"^(?:please |can you |could you |okay |ok |hey |pode |por favor |ei )+", "", text)
    return re.sub(r"(?: please| for me| a bit| a little| por favor| um pouco)+$", "", text)


def control(prompt: str, spotify: bool = False) -> str | None:
    """pause, resume, stop, louder, quieter (and next, previous on Spotify) — or None."""
    text = _control_text(prompt)
    return _LOOKUP.get(text) or (_SPOTIFY_LOOKUP.get(text) if spotify else None)


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
            # start/end play one section of a video: one fight from a commentator's breakdown.
            section = "".join(f"&{key}={float(info[key]):.2f}" for key in ("start", "end") if info.get(key) is not None)
            self._thread = threading.Thread(target=self._run, args=(info["id"] + section, self._stop), daemon=True)
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


class SpotifyRemote:
    """Spotify playing in his own app, steered through the voice server.

    It only knows what it started: once the server says Spotify is playing, it
    counts as the music in the room until "stop". Each control is a short HTTP
    call, sent on a thread so ducking never holds up his voice.
    """

    def __init__(self, voice_url: str = "http://127.0.0.1:5051", send=None):
        self.voice_url = voice_url
        self.send = send or self._post
        self.title = None
        self._active = False
        self._paused = False
        self._ducks = 0

    @property
    def active(self) -> bool:
        return self._active

    @property
    def paused(self) -> bool:
        return self._active and self._paused

    def _post(self, action: str) -> None:
        request = urllib.request.Request(f"{self.voice_url}/spotify", data=json.dumps({"action": action}).encode(),
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                result = json.loads(response.read() or b"{}")
            if not result.get("ok", True):
                print(f"  spotify {action}: {result.get('error')}")
        except Exception as exc:
            print(f"  spotify {action} failed: {exc}")

    def _later(self, action: str) -> None:
        threading.Thread(target=self.send, args=(action,), daemon=True).start()

    def play(self, info: dict) -> None:
        """The server has already started it; this only takes note."""
        self.title = info.get("title")
        self._active, self._paused = True, False

    def pause(self) -> None:
        self._paused = True
        self._later("pause")

    def resume(self) -> None:
        self._paused = False
        self._later("resume")

    def stop(self) -> None:
        if self._active:
            self._later("pause")
        self._active, self._paused, self.title = False, False, None

    def louder(self) -> None:
        self._later("louder")

    def quieter(self) -> None:
        self._later("quieter")

    def next(self) -> None:
        self._later("next")

    def previous(self) -> None:
        self._later("previous")

    def apply(self, action: str) -> None:
        getattr(self, action)()

    def duck(self) -> None:
        self._ducks += 1
        if self._ducks == 1 and self._active and not self._paused:
            self._later("duck")

    def unduck(self) -> None:
        if self._ducks == 0:
            return
        self._ducks -= 1
        if self._ducks == 0 and self._active and not self._paused:
            self._later("unduck")


class Jukebox:
    """The YouTube player and the Spotify remote as one: whichever started last is the music."""

    def __init__(self, player: MusicPlayer, spotify: SpotifyRemote):
        self.player = player
        self.spotify = spotify

    @property
    def current(self):
        return self.spotify if self.spotify.active else self.player

    @property
    def active(self) -> bool:
        return self.player.active or self.spotify.active

    @property
    def paused(self) -> bool:
        return self.current.paused

    def play(self, info: dict) -> None:
        if info.get("source") == "spotify":
            self.player.stop()
            self.spotify.play(info)
        else:
            self.spotify.stop()
            self.player.play(info)

    def control(self, prompt: str) -> str | None:
        return control(prompt, spotify=self.spotify.active)

    def apply(self, action: str) -> None:
        self.current.apply(action)

    def stop(self) -> None:
        self.player.stop()
        self.spotify.stop()

    # Ducking goes to both: the remote only sends anything while Spotify is on.
    def duck(self) -> None:
        self.player.duck()
        self.spotify.duck()

    def unduck(self) -> None:
        self.player.unduck()
        self.spotify.unduck()
