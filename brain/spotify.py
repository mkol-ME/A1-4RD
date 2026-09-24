"""Spotify through its Web API: Alfred is the remote, a Spotify app is the speaker.

Nothing is streamed through Alfred. The Web API tells one of the owner's own
Spotify apps (the laptop's, usually) what to play, pause or skip, which needs a
Premium account and nothing else. A Spotify Connect receiver on the Pi can be
that app later without changing any of this.

Sign-in happens once, on the server, with the browser on the laptop:

  1. Make an app at developer.spotify.com/dashboard. Redirect URI
     http://127.0.0.1:8765/callback, API "Web API". Copy its Client ID.
  2. ssh -L 8765:127.0.0.1:8765 <server> \
         "cd ~/a1-4rd && .venv-rvc/bin/python brain/spotify.py login CLIENT_ID"
  3. Open the link it prints on the laptop and agree. The redirect comes back
     through the tunnel and the server keeps a refresh token.

It uses PKCE, so there is no client secret anywhere. The token lives in
ALFRED_SPOTIFY_CONFIG (default ~/.config/a1-4rd/spotify.json, mode 600), never
in the repository.

    python brain/spotify.py devices | now | play "query" | pause | resume
"""

import base64
import hashlib
import json
import os
import re
import secrets
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path(os.environ.get("ALFRED_SPOTIFY_CONFIG", "~/.config/a1-4rd/spotify.json")).expanduser()
PORT = int(os.environ.get("ALFRED_SPOTIFY_PORT", "8765"))
REDIRECT = f"http://127.0.0.1:{PORT}/callback"
SCOPES = ("user-read-playback-state user-modify-playback-state user-read-currently-playing "
          "user-library-read playlist-read-private playlist-read-collaborative")
API = "https://api.spotify.com/v1"
ACCOUNTS = "https://accounts.spotify.com"
TIMEOUT = 6

VOLUME_STEP = 1.5          # louder/quieter, as the client's own player does
DUCKED = 0.15              # while he talks or is being answered
_ducked_from: list = []    # the volume to go back to, while ducked


class SpotifyError(Exception):
    """`code` is what went wrong in a word the voice server can pick a line by."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


# --- the token ---------------------------------------------------------------

def _load() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(config: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(CONFIG)


def configured() -> bool:
    config = _load()
    return bool(config.get("client_id") and config.get("refresh_token"))


def _post_form(url: str, fields: dict) -> dict:
    request = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(),
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise SpotifyError("auth", exc.read().decode("utf-8", "replace")[:200]) from exc
    except OSError as exc:
        raise SpotifyError("unreachable", str(exc)) from exc


def _token(force: bool = False) -> str:
    config = _load()
    if not (config.get("client_id") and config.get("refresh_token")):
        raise SpotifyError("not_configured")
    if not force and config.get("access_token") and config.get("expires_at", 0) - 60 > time.time():
        return config["access_token"]
    fresh = _post_form(f"{ACCOUNTS}/api/token", {"grant_type": "refresh_token",
                                                 "refresh_token": config["refresh_token"],
                                                 "client_id": config["client_id"]})
    config["access_token"] = fresh["access_token"]
    config["expires_at"] = time.time() + int(fresh.get("expires_in", 3600))
    # PKCE refresh tokens rotate: the old one stops working once a new one is issued.
    config["refresh_token"] = fresh.get("refresh_token") or config["refresh_token"]
    _save(config)
    return config["access_token"]


def _call(method: str, path: str, params: dict | None = None, body: dict | None = None,
          retry: bool = True):
    url = f"{API}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    data = json.dumps(body).encode() if body is not None else (b"" if method in ("PUT", "POST") else None)
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={"Authorization": f"Bearer {_token()}",
                                              "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", "replace")
        if exc.code == 401 and retry:
            _token(force=True)
            return _call(method, path, params, body, retry=False)
        if exc.code == 404 and "NO_ACTIVE_DEVICE" in text:
            raise SpotifyError("no_device") from exc
        if exc.code == 403 and "PREMIUM_REQUIRED" in text:
            raise SpotifyError("premium") from exc
        if exc.code == 403 and "VOLUME_CONTROL_DISALLOW" in text:
            raise SpotifyError("no_volume") from exc
        raise SpotifyError("http", f"{exc.code} {text[:200]}") from exc
    except OSError as exc:
        raise SpotifyError("unreachable", str(exc)) from exc


# --- finding the thing he asked for -------------------------------------------

def plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower()).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.replace("'", "")))


LIKED = re.compile(r"^(?:my |all my )?(?:liked|saved|favou?rite|loved) (?:songs|tracks|music)$|^my (?:likes|favou?rites)$")
PLAYLIST = re.compile(r"^(?:my |the )?(?P<name>.+?) playlist$|^(?:my |the )?playlist (?:called |named )?(?P<name2>.+)$")
ALBUM = re.compile(r"^(?:the )?(?P<name>.+?) album$|^(?:the )?album (?P<name2>.+)$")
BY = re.compile(r"^(?P<track>.+?) by (?P<artist>.+)$")


def wants_spotify(query: str) -> bool:
    """Things only Spotify has: his own liked songs and playlists."""
    q = plain(query)
    return bool(LIKED.match(q) or q.startswith("my ") and PLAYLIST.match(q))


def _same(a: str, b: str) -> bool:
    strip = lambda s: re.sub(r"^the ", "", plain(s))  # noqa: E731
    return strip(a) == strip(b)


def _artists(item: dict) -> str:
    return ", ".join(a["name"] for a in item.get("artists", [])[:2])


def find(query: str) -> dict:
    """What to play for this request: {"title": spoken name, and "context" or "uris"}."""
    q = plain(query)
    if LIKED.match(q):
        saved = _call("GET", "/me/tracks", {"limit": 50}) or {}
        uris = [row["track"]["uri"] for row in saved.get("items", []) if row.get("track")]
        if not uris:
            raise SpotifyError("no_match")
        return {"title": "your liked songs", "uris": uris, "shuffle": True}

    found = PLAYLIST.match(q)
    if found:
        name = found.group("name") or found.group("name2")
        page, offset = None, 0
        while offset < 200:
            page = _call("GET", "/me/playlists", {"limit": 50, "offset": offset}) or {}
            for item in page.get("items", []):
                if item and _same(item.get("name", ""), name):
                    return {"title": item["name"], "context": item["uri"]}
            if not page.get("next"):
                break
            offset += 50
        hits = (_call("GET", "/search", {"q": name, "type": "playlist", "limit": 5}) or {})
        items = [i for i in hits.get("playlists", {}).get("items", []) if i]
        if items:
            return {"title": items[0]["name"], "context": items[0]["uri"]}
        raise SpotifyError("no_match")

    found = ALBUM.match(q)
    if found:
        name = found.group("name") or found.group("name2")
        hits = _call("GET", "/search", {"q": name, "type": "album", "limit": 5}) or {}
        items = hits.get("albums", {}).get("items", [])
        if items:
            album = items[0]
            return {"title": f"{album['name']} by {_artists(album)}", "context": album["uri"]}
        raise SpotifyError("no_match")

    found = BY.match(q)
    if found:
        hits = _call("GET", "/search", {"q": f"track:{found.group('track')} artist:{found.group('artist')}",
                                         "type": "track", "limit": 5}) or {}
        items = hits.get("tracks", {}).get("items", [])
        if items:
            return {"title": f"{items[0]['name']} by {_artists(items[0])}", "uris": [items[0]["uri"]]}

    hits = _call("GET", "/search", {"q": query, "type": "artist,track", "limit": 5}) or {}
    artists = hits.get("artists", {}).get("items", [])
    tracks = hits.get("tracks", {}).get("items", [])
    # "Play Drake" is the artist; "play hotline bling" is the song. An artist
    # only when the request is his name and nothing else.
    artist = next((a for a in artists if _same(a["name"], q)), None)
    if artist is not None:
        return {"title": artist["name"], "context": artist["uri"], "shuffle": True}
    if tracks:
        return {"title": f"{tracks[0]['name']} by {_artists(tracks[0])}", "uris": [tracks[0]["uri"]]}
    raise SpotifyError("no_match")


# --- which app plays it ---------------------------------------------------------

def devices() -> list[dict]:
    return (_call("GET", "/me/player/devices") or {}).get("devices", [])


def pick_device(found: list[dict]) -> dict | None:
    """The app already playing, else a computer (the laptop), else anything that can play."""
    usable = [d for d in found if not d.get("is_restricted")]
    return (next((d for d in usable if d.get("is_active")), None)
            or next((d for d in usable if d.get("type") == "Computer"), None)
            or (usable[0] if usable else None))


def play(query: str) -> dict:
    """Start it on his device. Returns {"source": "spotify", "title": ...}."""
    target = find(query)
    device = pick_device(devices())
    if device is None:
        raise SpotifyError("no_device")
    body = {"context_uri": target["context"]} if target.get("context") else {"uris": target["uris"]}
    params = {"device_id": device["id"]}
    if target.get("shuffle") is not None:
        try:
            _call("PUT", "/me/player/shuffle", dict(params, state="true" if target["shuffle"] else "false"))
        except SpotifyError:
            pass            # a device that was idle may refuse this until it plays; not worth failing for
    _call("PUT", "/me/player/play", params, body)
    _ducked_from.clear()
    return {"source": "spotify", "title": target["title"], "device": device.get("name")}


# --- the controls the client sends while it plays -------------------------------

def _volume() -> int | None:
    state = _call("GET", "/me/player") or {}
    return (state.get("device") or {}).get("volume_percent")


def set_volume(percent: float) -> None:
    _call("PUT", "/me/player/volume", {"volume_percent": int(max(0, min(100, round(percent))))})


def control(action: str) -> dict:
    """pause, resume, stop, next, previous, louder, quieter, duck, unduck, now."""
    if action in ("pause", "stop"):
        _call("PUT", "/me/player/pause")
    elif action == "resume":
        _call("PUT", "/me/player/play")
    elif action == "next":
        _call("POST", "/me/player/next")
    elif action == "previous":
        _call("POST", "/me/player/previous")
    elif action in ("louder", "quieter"):
        now = _ducked_from[0] if _ducked_from else (_volume() or 50)
        louder = action == "louder"
        target = max(now * VOLUME_STEP, now + 5) if louder else min(now / VOLUME_STEP, now - 5)
        if _ducked_from:
            _ducked_from[0] = max(0, min(100, round(target)))    # takes effect when he stops talking
        else:
            set_volume(target)
    elif action == "duck":
        if not _ducked_from:
            now = _volume()
            if now:
                _ducked_from.append(now)
                set_volume(now * DUCKED)
    elif action == "unduck":
        if _ducked_from:
            set_volume(_ducked_from.pop())
    elif action == "now":
        return {"ok": True, "playing": now_playing()}
    else:
        raise SpotifyError("unknown_action", action)
    return {"ok": True}


def now_playing() -> str | None:
    state = _call("GET", "/me/player/currently-playing") or {}
    item = state.get("item")
    if not item:
        return None
    return f"{item['name']} by {_artists(item)}" if item.get("artists") else item.get("name")


# --- one-time sign-in ---------------------------------------------------------------

def login(client_id: str) -> None:
    from http.server import BaseHTTPRequestHandler, HTTPServer

    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    link = f"{ACCOUNTS}/authorize?" + urllib.parse.urlencode({
        "client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPES,
        "state": state, "code_challenge_method": "S256", "code_challenge": challenge})
    got: dict = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if not self.path.startswith("/callback"):
                self.send_error(404)
                return
            got.update({key: values[0] for key, values in query.items()})
            ok = got.get("state") == state and "code" in got
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Signed in. You can close this tab." if ok else b"Sign-in failed. Check the terminal.")

        def log_message(self, *args):
            return

    print("Open this on the laptop (the ssh -L tunnel carries the reply back here):\n")
    print(link + "\n")
    server = HTTPServer(("127.0.0.1", PORT), Callback)
    while "code" not in got and "error" not in got:
        server.handle_request()
    server.server_close()
    if got.get("state") != state or "code" not in got:
        sys.exit(f"sign-in failed: {got.get('error') or 'state did not match'}")
    token = _post_form(f"{ACCOUNTS}/api/token", {
        "grant_type": "authorization_code", "code": got["code"], "redirect_uri": REDIRECT,
        "client_id": client_id, "code_verifier": verifier})
    _save({"client_id": client_id, "refresh_token": token["refresh_token"],
           "access_token": token["access_token"],
           "expires_at": time.time() + int(token.get("expires_in", 3600))})
    print(f"Saved to {CONFIG}.")
    try:
        names = [f"{d['name']} ({d['type']}{', active' if d.get('is_active') else ''})" for d in devices()]
        print("Spotify apps it can see now: " + (", ".join(names) or "none open"))
    except SpotifyError as exc:
        print(f"Signed in, but listing devices failed: {exc}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    command, rest = sys.argv[1], " ".join(sys.argv[2:])
    try:
        if command == "login":
            login(rest.strip())
        elif command == "devices":
            for device in devices():
                print(device)
        elif command == "now":
            print(now_playing())
        elif command == "play":
            print(play(rest))
        else:
            print(control(command))
    except SpotifyError as exc:
        print(f"spotify: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
