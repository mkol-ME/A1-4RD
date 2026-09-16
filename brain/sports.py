"""Scores, results and fixtures from ESPN, instead of from search snippets.

Asked "who's going to win copa libertadores", the web search came back with the
2024 final. Sport is the clearest case of a question whose answer changes by the
hour, and search pages are always a day or a season behind. ESPN's own site
serves the scoreboards as JSON: no account, no key, 0.2-0.5s.

One quirk worth knowing: site.api.espn.com refuses a browser User-Agent with
403 while site.web.api.espn.com answers either way, so only the latter is used.

Everything is phrased for the answerer as current data with the time it was
fetched, in the same spirit as weather.py: if it disagrees with anything said
earlier, this is right.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API = "https://site.web.api.espn.com/apis"
TIMEOUT = 8
TIMEZONE = os.environ.get("ALFRED_TIMEZONE", "America/New_York")
MAX_EVENTS = 8
SPORTS = {"football", "baseball", "basketball", "hockey", "soccer", "mma", "racing"}


def _get(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())


# Words that say which sport but make ESPN's search find nothing: "notre dame
# football" matched no team at all, "notre dame" matched the right one.
SPORT_WORDS = {"football": "football", "basketball": "basketball", "baseball": "baseball",
               "hockey": "hockey", "soccer": "soccer", "mma": "mma", "racing": "racing"}
FILLER = {"game", "games", "score", "scores", "schedule", "match", "fixture", "fixtures",
          "team", "result", "results", "season", "the", "tonight", "today"}


def find(query: str) -> dict | None:
    """The team, league or fighter ESPN thinks the query means."""
    words = query.lower().split()
    sport = next((SPORT_WORDS[w] for w in words if w in SPORT_WORDS), None)
    cleaned = " ".join(w for w in words if w not in SPORT_WORDS and w not in FILLER) or query.lower()
    data = _get(f"{API}/search/v2?" + urllib.parse.urlencode({"query": cleaned, "limit": 5}))
    candidates = []
    for block in data.get("results", []):
        if block.get("type") not in ("team", "league", "player"):
            continue
        for item in block.get("contents", []):
            if item.get("sport") in SPORTS and (sport is None or item.get("sport") == sport):
                candidates.append(item)

    def rank(item: dict) -> int:
        name = (item.get("displayName") or "").lower()
        if item.get("type") == "league" and cleaned in (item.get("defaultLeagueSlug") or "", name):
            return 0      # "nhl", "premier league": the league, not a player called Nhlanhla
        if item.get("type") == "league" and cleaned in name:
            return 1
        if item.get("type") == "team":
            return 2
        if item.get("type") == "league":
            return 3
        return 4          # players last: only a fighter's name should land here
    return min(candidates, key=rank) if candidates else None


def when(stamp: str) -> str:
    """'2026-09-20T17:00Z' as 'Sunday 1:00 PM' in the user's time zone."""
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(ZoneInfo(TIMEZONE))
    except Exception:
        return stamp
    return f"{moment.strftime('%A %b')} {moment.day}, {moment.hour % 12 or 12}:{moment.minute:02d} {moment.strftime('%p')}"


def describe_event(event: dict) -> str:
    """One line for one game, fight card or race."""
    competition = (event.get("competitions") or [{}])[0]
    status = (competition.get("status") or event.get("status") or {})
    state = (status.get("type") or {}).get("state")          # pre, in, post
    detail = (status.get("type") or {}).get("shortDetail") or (status.get("type") or {}).get("description") or ""
    competitors = competition.get("competitors") or []
    name = event.get("name") or ""
    sides = []
    for side in competitors:
        team = side.get("team") or side.get("athlete") or {}
        label = team.get("displayName") or team.get("shortDisplayName") or "?"
        score = side.get("score")
        if isinstance(score, dict):
            score = score.get("displayValue")
        sides.append((label, score, side.get("winner")))
    if len(competitors) > 2 or any(len(c.get("competitors") or []) > 2 for c in event.get("competitions") or []):
        # A race: the podium, not twenty-two names.
        race = next((c for c in reversed(event.get("competitions") or [])
                     if len(c.get("competitors") or []) > 2), competition)
        field = sorted(race.get("competitors") or [], key=lambda c: c.get("order") or 99)
        podium = [((c.get("athlete") or c.get("team") or {}).get("displayName") or "?") for c in field[:3]]
        race_state = ((race.get("status") or {}).get("type") or {}).get("state") or state
        if race_state == "post" and podium:
            return f"{name}: finished, won by {podium[0]}, then {', '.join(podium[1:])}"
        return f"{name}: {when(race.get('date') or event.get('date', ''))}" + (
            " (happening now)" if race_state == "in" else "")
    if event.get("competitions") and len(event["competitions"]) > 1:
        # A fight card: the last bout listed is the main event.
        main = event["competitions"][-1]
        fighters = [((c.get("athlete") or {}).get("displayName") or "?") for c in main.get("competitors", [])]
        if not fighters:
            # A race weekend before the grid is set: practice, qualifying, race.
            # The last session is the race, and its date is the one that matters.
            return f"{name}: {when(main.get('date') or event.get('date', ''))}"
        winner = next(((c.get("athlete") or {}).get("displayName") for c in main.get("competitors", [])
                       if c.get("winner")), None)
        headline = f"{name}, main event {' vs '.join(fighters)}"
        if state == "post":
            return f"{headline}: finished" + (f", {winner} won" if winner else "")
        # The event date is when the card starts; the main event is hours later.
        return f"{headline}: card starts {when(event.get('date', ''))}" + (
            " (happening now)" if state == "in" else "")
    if len(sides) == 2 and state in ("in", "post"):
        (a, a_score, a_won), (b, b_score, b_won) = sides
        score = f"{a} {a_score}, {b} {b_score}"
        if state == "in":
            return f"LIVE: {score} ({detail})"
        winner = a if a_won else b if b_won else None
        return f"Final, {when(event.get('date', ''))}: {score}" + (f", {winner} won" if winner else "")
    return f"{name}: {when(event.get('date', ''))}" + (f" ({detail})" if state == "in" else "")


def team_report(item: dict) -> str:
    sport, league = item["sport"], item.get("defaultLeagueSlug")
    team_id = re.search(r"~t:(\d+)", item.get("uid", ""))
    if not league or not team_id:
        return ""
    base = f"{API}/site/v2/sports/{sport}/{league}/teams/{team_id.group(1)}/schedule"
    data = _get(base)
    events = list(data.get("events") or [])
    if sport == "soccer":
        # Soccer schedules list played games only unless fixtures are asked for.
        try:
            events += _get(base + "?fixture=true").get("events") or []
        except Exception:
            pass
    # Two lists joined, and neither promises an order; "last game" means by date.
    seen, ordered = set(), []
    for event in sorted(events, key=lambda e: e.get("date") or ""):
        if event.get("id") not in seen:
            seen.add(event.get("id"))
            ordered.append(event)
    events = ordered
    played = [e for e in events if _state(e) == "post"]
    live = [e for e in events if _state(e) == "in"]
    upcoming = [e for e in events if _state(e) == "pre"]
    record = (data.get("team") or {}).get("recordSummary")
    lines = [f"{item['displayName']} ({item.get('subtitle') or league})" + (f", record {record}" if record else "")]
    for event in live:
        lines.append("- " + describe_event(event))
    if played:
        lines.append("- Last game: " + describe_event(played[-1]))
    if upcoming:
        lines.append("- Next game: " + describe_event(upcoming[0]))
    return "\n".join(lines)


def league_report(item: dict) -> str:
    sport, league = item["sport"], item.get("defaultLeagueSlug")
    if not league:
        return ""
    url = f"{API}/site/v2/sports/{sport}/{league}/scoreboard"
    if sport in ("mma", "racing"):
        # A fight card or a race is a weekend, not a nightly slate: the current
        # scoreboard is only this week, so "the next UFC event" was never on it.
        today = datetime.now(timezone.utc)
        start = today.fromordinal(today.toordinal() - 10).strftime("%Y%m%d")
        end = today.fromordinal(today.toordinal() + 60).strftime("%Y%m%d")
        events = _get(f"{url}?dates={start}-{end}").get("events") or []
        events.sort(key=lambda e: e.get("date") or "")
        finished = [e for e in events if _state(e) == "post"][-1:]
        coming = [e for e in events if _state(e) != "post"][:3]
        events = finished + coming
    else:
        events = _get(url).get("events") or []
    lines = [f"{item['displayName']}, recent and upcoming:" if sport in ("mma", "racing")
             else f"{item['displayName']}, current scoreboard:"]
    lines.extend("- " + describe_event(event) for event in events[:MAX_EVENTS])
    if not events:
        lines.append("- Nothing scheduled on the current scoreboard.")
    return "\n".join(lines)


def _state(event: dict) -> str | None:
    competition = (event.get("competitions") or [{}])[0]
    status = competition.get("status") or event.get("status") or {}
    return (status.get("type") or {}).get("state")


def lookup(query: str) -> dict:
    """Result shaped like the other tools: ok, found, and text for the answerer."""
    item = find(query)
    if item is None:
        return {"ok": True, "found": 0, "note": f"ESPN has no team, league or fighter matching '{query}'."}
    if item.get("type") == "team":
        report = team_report(item)
    elif item.get("type") == "league":
        report = league_report(item)
    else:
        report = ""
    if not report:
        return {"ok": True, "found": 0,
                "note": f"ESPN knows {item.get('displayName')} but has no schedule for it; search the web."}
    stamp = datetime.now(timezone.utc).astimezone(ZoneInfo(TIMEZONE))
    header = (f"Sports data from ESPN, fetched {stamp.hour % 12 or 12}:{stamp.minute:02d} "
              f"{stamp.strftime('%p')}. This is current; prefer it over anything said earlier:")
    return {"ok": True, "found": 1, "report": f"{header}\n{report}"}


if __name__ == "__main__":
    import sys
    result = lookup(" ".join(sys.argv[1:]) or "chicago bears")
    print(result.get("report") or result.get("note"))
