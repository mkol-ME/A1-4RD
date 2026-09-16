"""The weather, from a forecast service instead of from search snippets.

Asked the temperature on 2026-09-16 he said 78; it was 92. The web search had
done its job and returned pages about the weather — cached, dated, some for the
wrong day — and he quoted the nearest number with total confidence. A forecast
is not a fact that search can check. It needs a source that is about now.

Open-Meteo: free, no account, no key, and 0.55s from the server. Results are
cached for ten minutes, so "and tomorrow" after "what's the weather" costs
nothing. Weather turns skip the decider and the web search entirely, which also
makes them faster than any other looked-up turn.

Home is not in this file, because the repository is public. It lives in
persona/location.local.txt (git-ignored), one line: `Name, latitude, longitude`.
Without it a place still has to be named, and a question with no place falls
back to the web search as before.
"""

import functools
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

TIMEOUT = 4
CACHE_SECONDS = 600
FOLLOW_UP_TURNS = 3
FORECAST_DAYS = 7
LOCAL_LOCATION = Path(__file__).resolve().parent.parent / "persona" / "location.local.txt"

# WMO weather interpretation codes, as Open-Meteo reports them.
CONDITIONS = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "heavy freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with heavy hail",
}

# Words that only mean the weather. "temperature" alone is not one of them:
# "what temperature should i run petg at" is a printing question.
ASKS = re.compile(
    r"\b(weather|forecast|rain(?:ing|y)?|snow(?:ing|y)?|storm(?:s|ing|y)?|thunderstorms?"
    r"|umbrella|humid(?:ity)?|drizzl(?:e|ing)|sunny|cloudy|windy"
    r"|(?:how )?(?:hot|cold|warm|chilly|freezing) (?:is it|out|outside|today|tonight|tomorrow)"
    r"|temp(?:erature)? (?:outside|out|today|tonight|tomorrow|this|right now"
    r"|(?:in|at|for|near) (?!my\b|the\b|your\b|here\b))"
    r"|degrees (?:outside|out)|need a (?:jacket|coat))\b",
    re.I)
# Enough to keep a follow-up on the weather once a recent question was. From the
# first voice session: "as of when alfred i have it as 92".
FOLLOWS = re.compile(
    r"\b(degrees|tomorrow|tonight|today|weekend|morning|afternoon|evening|monday|tuesday"
    r"|wednesday|thursday|friday|saturday|sunday|next week|hot|cold|warm|high|low"
    r"|outside|as of|\d{2,3})\b"
    r"|^(and|what about|how about) ",
    re.I)
# "for" and "at" name a place only straight after the weather word: "weather for
# chicago" is a place, "an umbrella for class" is not.
PLACE = re.compile(
    r"(?:\b(?:in|near)|\b(?:weather|forecast)(?: like)? (?:for|at)) ([a-z][a-z .'-]*)$", re.I)
TRAILING_TIME = re.compile(
    r"\s+(today|tonight|tomorrow|right now|now|like|this (?:week|weekend|morning|afternoon|evening)"
    r"|on (?:mon|tues|wednes|thurs|fri|satur|sun)day|next week)$", re.I)
NOT_A_PLACE = re.compile(
    r"^(?:the |a |an |my |this |that |here|there|all|least|general|fahrenheit|celsius|degrees)"
    r"|\b(?:hours?|minutes?|days?|weeks?|while|bit|morning|afternoon|evening|night)\b", re.I)

_cache: dict = {}


def asks_about_weather(prompt: str, history: list | None = None) -> bool:
    """Is this turn about the weather, on its own or as a follow-up?"""
    text = " ".join(prompt.lower().split())
    if ASKS.search(text):
        return True
    return bool(FOLLOWS.search(text) and _weather_question_before(history))


def _weather_question_before(history: list | None) -> str | None:
    """The latest weather question among the last few, if the conversation is on the weather.

    Only looking one question back broke on a chain: "what's the weather",
    "it's 92, where'd you get 78", "and tomorrow". The middle turn is not itself
    a weather question, so "and tomorrow" went without a forecast and he
    answered "ninety-two and sunny" for an overcast 94 (2026-09-16).
    """
    asked = [item.get("content", "") for item in (history or []) if item.get("role") == "user"]
    return next((text for text in reversed(asked[-FOLLOW_UP_TURNS:]) if ASKS.search(text)), None)


def named_place(prompt: str) -> str | None:
    """The place a question names, if it names one: 'weather in chicago tomorrow'."""
    text = re.sub(r"[?!.,]+", " ", prompt.lower())
    text = " ".join(text.split())
    while True:
        trimmed = TRAILING_TIME.sub("", text)
        if trimmed == text:
            break
        text = trimmed
    found = PLACE.search(text)
    if not found:
        return None
    place = found.group(1).strip(" .'-")
    if not place or NOT_A_PLACE.search(place):
        return None
    return place


def home() -> tuple[str, float, float] | None:
    """Where the user is, from the git-ignored local file."""
    raw = os.environ.get("ALFRED_LOCATION", "")
    if not raw and LOCAL_LOCATION.exists():
        raw = LOCAL_LOCATION.read_text(encoding="utf-8").strip()
    parts = [part.strip() for part in raw.rsplit(",", 2)]
    if len(parts) != 3:
        return None
    try:
        return parts[0], float(parts[1]), float(parts[2])
    except ValueError:
        return None


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return json.loads(response.read())


@functools.lru_cache(maxsize=64)
def geocode(place: str) -> tuple[str, float, float] | None:
    found = _get("https://geocoding-api.open-meteo.com/v1/search?"
                 + urllib.parse.urlencode({"name": place, "count": 1, "language": "en"}))
    hits = found.get("results") or []
    if not hits:
        return None
    hit = hits[0]
    region = hit.get("admin1") or hit.get("country") or ""
    name = f"{hit['name']}, {region}" if region else hit["name"]
    return name, float(hit["latitude"]), float(hit["longitude"])


def forecast(latitude: float, longitude: float) -> dict:
    key = (round(latitude, 2), round(longitude, 2))
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]
    data = _get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": latitude, "longitude": longitude,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,weather_code",
        # Fahrenheit and mph because that is what he says out loud. The number
        # is spoken, so it has to be in the unit he will argue with.
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "timezone": "auto", "forecast_days": FORECAST_DAYS,
    }))
    _cache[key] = (time.monotonic(), data)
    return data


def render(name: str, data: dict) -> str:
    """The forecast, phrased for the answerer. Degrees are written as words for the voice."""
    now = data["current"]
    daily = data["daily"]
    stamp = datetime.fromisoformat(now["time"])
    lines = [
        f"Weather for {name} from Open-Meteo, a live forecast service, as of "
        f"{stamp.hour % 12 or 12}:{stamp.minute:02d} {stamp.strftime('%p')}. These are the "
        f"current numbers: if they differ from anything said earlier in this conversation, "
        f"these are right and the earlier figure was wrong.",
        f"- Now: {round(now['temperature_2m'])} degrees, feels like "
        f"{round(now['apparent_temperature'])}, {CONDITIONS.get(now['weather_code'], 'unsettled')}, "
        f"humidity {now['relative_humidity_2m']} percent, wind {round(now['wind_speed_10m'])} mph.",
    ]
    for index, day in enumerate(daily["time"]):
        label = ("Today" if index == 0 else "Tomorrow" if index == 1
                 else datetime.fromisoformat(day).strftime("%A"))
        rain = daily["precipitation_probability_max"][index]
        lines.append(
            f"- {label}: high {round(daily['temperature_2m_max'][index])}, low "
            f"{round(daily['temperature_2m_min'][index])}, "
            f"{CONDITIONS.get(daily['weather_code'][index], 'unsettled')}"
            + (f", {rain} percent chance of rain." if rain is not None else "."))
    return "\n".join(lines)


def lookup(prompt: str, history: list | None = None) -> str | None:
    """Forecast text for this turn, or None to fall back to the web search.

    A named place is looked up on the turn that names it; a follow-up such as
    "and tomorrow" keeps the place from the question before it. Only a bare
    follow-up inherits: "what's the weather like today" asked after "what's the
    weather in chicago" is about home, and answering it with Chicago's drizzle is
    exactly what happened when it did inherit.
    """
    place = named_place(prompt)
    if place is None and not ASKS.search(prompt) and FOLLOWS.search(prompt):
        previous = _weather_question_before(history)
        if previous:
            place = named_place(previous)
    try:
        where = geocode(place) if place else home()
        if where is None:
            return None
        name, latitude, longitude = where
        return render(name, forecast(latitude, longitude))
    except Exception:
        return None


if __name__ == "__main__":
    import sys
    print(lookup(" ".join(sys.argv[1:]) or "whats the weather") or "no forecast (set location)")
