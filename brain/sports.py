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
from concurrent.futures import ThreadPoolExecutor
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
    """The team, league or fighter ESPN thinks the query means.

    ESPN's search finds nothing for a matchup ("makhachev garry" returned only
    articles), so a query that finds nothing is retried a name at a time; the
    first fighter's record covers the fight between them.
    """
    found = _find(query)
    if found is not None:
        return found
    # Short names are skipped: "van" alone is Vanderbilt. "pantoja van" still
    # tries "pantoja", whose next fight is the one being asked about.
    parts = [p for p in re.split(r"\s+(?:vs\.?|v|versus|and)\s+|\s+", query.lower()) if len(p) >= 4]
    for part in parts if len(query.split()) > 1 else []:
        found = _find(part)
        if found is not None:
            return found
    return None


def _find(query: str) -> dict | None:
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
    """'2026-09-20T17:00Z' as 'Sunday 1:00 PM' in the owner's time zone."""
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(ZoneInfo(TIMEZONE))
    except Exception:
        return stamp
    # Without the year, a fight from 2024 read as last November's.
    if abs((moment - datetime.now(moment.tzinfo)).days) > 150:
        return f"{moment.strftime('%b')} {moment.day}, {moment.year}"
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
    detailed = False
    for event in events[:MAX_EVENTS]:
        lines.append("- " + describe_event(event))
        # The card that is on now, or else the next one, gets the fight-by-fight
        # view: the bout in progress with its stats, results so far, odds.
        if sport == "mma" and not detailed and _state(event) in ("in", "pre") and event.get("id"):
            detailed = True
            lines.extend(_try(card_report, event, league) or [])
    if not events:
        lines.append("- Nothing scheduled on the current scoreboard.")
    return "\n".join(lines)


CORE = "https://sports.core.api.espn.com/v2/sports/mma"


def _ref(link: dict) -> dict:
    return _get(link["$ref"].replace("http://", "https://"))


METHODS = {"koTkoDq": "KO/TKO", "submission": "submission", "points": "decision"}


def _try(function, *args):
    try:
        return function(*args)
    except Exception:
        return None


def bout(url: str) -> dict:
    """Everything ESPN has on one fight: who, status, stats, judges' scores, odds.

    Stats and the status update during the fight — the same fields that carry a
    finished fight's numbers — so this is also the live view. Odds are
    DraftKings', and ESPN only keeps them until the fight is over.
    """
    url = url.split("?")[0].replace("http://", "https://")
    competition = _get(url)
    competitors = competition.get("competitors") or []
    with ThreadPoolExecutor(max_workers=8) as pool:
        status = pool.submit(_ref, competition["status"])
        names = {str(c["id"]): pool.submit(_try, _ref, c["athlete"]) for c in competitors if "athlete" in c}
        stats = {str(c["id"]): pool.submit(_try, _ref, c["statistics"]) for c in competitors if "statistics" in c}
        scores = {str(c["id"]): pool.submit(_try, _ref, c["linescores"]) for c in competitors if "linescores" in c}
        odds = pool.submit(_try, _get, url + "/odds")
        status = status.result()
        names = {k: ((v.result() or {}).get("displayName") or "?") for k, v in names.items()}
        stats = {k: v.result() for k, v in stats.items()}
        scores = {k: v.result() for k, v in scores.items()}
        odds = odds.result()
    state = (status.get("type") or {}).get("state")
    result = {
        "date": competition.get("date"), "state": state, "names": names,
        "period": status.get("period"), "clock": status.get("displayClock"),
        "method": (status.get("result") or {}).get("displayName"),
        "winner": next((str(c["id"]) for c in competitors if c.get("winner")), None),
        "stats": {}, "scores": [], "odds": None,
    }
    for fighter, data in stats.items():
        values = {s["name"]: s.get("displayValue") for cat in ((data or {}).get("splits") or {}).get("categories", [])
                  for s in cat.get("stats", [])}
        result["stats"][fighter] = values
    judges = {}
    for fighter, data in scores.items():
        for total in (data or {}).get("items", []):
            for card in total.get("linescores") or []:
                judges.setdefault(card.get("order"), {})[fighter] = card.get("displayValue")
    result["scores"] = [judges[order] for order in sorted(judges, key=lambda o: o or 0)]
    for item in (odds or {}).get("items", []):
        sides = {}
        for key in ("homeAthleteOdds", "awayAthleteOdds"):
            side = item.get(key) or {}
            fighter = re.search(r"athletes/(\d+)", (side.get("athlete") or {}).get("$ref", ""))
            if not fighter or side.get("moneyLine") is None:
                continue
            methods = ((side.get("current") or {}).get("victoryMethod")
                       or (side.get("open") or {}).get("victoryMethod") or {})
            sides[fighter.group(1)] = {
                "moneyline": side["moneyLine"], "favorite": side.get("favorite"),
                "methods": {METHODS.get(k, k): v.get("american") for k, v in methods.items() if v.get("american")},
            }
        if sides:
            result["odds"] = {"provider": (item.get("provider") or {}).get("name") or "sportsbook",
                              "sides": sides, "rounds": item.get("overUnder")}
            break
    return result


def _american(value) -> str:
    return f"+{value}" if isinstance(value, (int, float)) and value > 0 else str(value)


def odds_text(details: dict) -> str:
    odds = details.get("odds")
    if not odds:
        return ""
    parts = []
    for fighter, side in odds["sides"].items():
        name = details["names"].get(fighter, "?")
        methods = ", ".join(f"by {m} {_american(p)}" for m, p in side["methods"].items())
        parts.append(f"{name} {_american(side['moneyline'])}" + (" (favourite)" if side.get("favorite") else "")
                     + (f" [{methods}]" if methods else ""))
    rounds = f"; over/under {odds['rounds']} rounds" if odds.get("rounds") else ""
    return f" Odds ({odds['provider']}, American moneyline): " + "; ".join(parts) + rounds + "."


def stats_text(details: dict) -> str:
    parts = []
    for fighter, values in details["stats"].items():
        if not values:
            continue
        bits = []
        if values.get("knockDowns") not in (None, "0"):
            bits.append(f"{values['knockDowns']} knockdown{'s' if values['knockDowns'] != '1' else ''}")
        if values.get("sigStrikesAttempted") not in (None, "0"):
            bits.append(f"{values.get('sigStrikesLanded')} of {values['sigStrikesAttempted']} significant strikes")
        if values.get("takedownsAttempted") not in (None, "0"):
            bits.append(f"{values.get('takedownsLanded')} of {values['takedownsAttempted']} takedowns")
        if values.get("timeInControl") not in (None, "0:00", "0"):
            bits.append(f"{values['timeInControl']} control time")
        if bits:
            parts.append(f"{details['names'].get(fighter, '?')}: " + ", ".join(bits))
    return (" Stats — " + "; ".join(parts) + ".") if parts else ""


def scores_text(details: dict, fighter: str) -> str:
    cards = [f"{card.get(fighter)}-{next((v for k, v in card.items() if k != fighter), '?')}"
             for card in details["scores"] if card.get(fighter)]
    return f" Judges scored it {', '.join(cards)} for {details['names'].get(fighter, '?')}." if cards else ""


def fight_line(entry: dict, fighter_id: str) -> str:
    """'UFC 309, Nov 16 2024: beat Stipe Miocic by KO/TKO in round 3 (4:29)', with
    odds before a fight, round, clock and stats during it, and scores after."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        details = pool.submit(bout, entry["competition"]["$ref"])
        event = pool.submit(_ref, entry["event"])
        details, event = details.result(), event.result()
    opponent = next((n for k, n in details["names"].items() if k != fighter_id), "an unknown opponent")
    name = event.get("name") or "a fight"
    date = when(details.get("date") or event.get("date") or "")
    if details["state"] == "pre":
        return f"{name}, {date}: against {opponent}.{odds_text(details)}"
    if details["state"] == "in":
        return (f"{name}: LIVE NOW against {opponent}, round {details['period']}, {details['clock']} on the clock."
                f"{stats_text(details)}{odds_text(details)}")
    method = details["method"] or "decision"
    finish = (f" in round {details['period']} ({details['clock']})"
              if details["period"] and "decision" not in method.lower() else "")
    verb = "beat" if details["winner"] == fighter_id else "lost to"
    return (f"{name}, {date}: {verb} {opponent} by {method}{finish}."
            f"{scores_text(details, details['winner']) if 'decision' in method.lower() and details['winner'] else ''}"
            f"{stats_text(details)}")


def card_report(event: dict, league: str) -> list[str]:
    """A fight card: live bout with stats, latest results, what is next; odds on the main event."""
    base = f"{CORE}/leagues/{league}/events/{event['id']}/competitions"
    bouts = event.get("competitions") or []
    state = lambda b: ((b.get("status") or {}).get("type") or {}).get("state")
    finished = [b for b in bouts if state(b) == "post"]
    live = [b for b in bouts if state(b) == "in"]
    coming = [b for b in bouts if state(b) == "pre"]
    names = lambda b: " vs ".join(((c.get("athlete") or {}).get("displayName") or "?") for c in b.get("competitors", []))
    lines = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        live_details = [pool.submit(bout, f"{base}/{b['id']}") for b in live]
        result_details = [pool.submit(_try, bout, f"{base}/{b['id']}") for b in finished[-3:]]
        main = pool.submit(_try, bout, f"{base}/{bouts[-1]['id']}") if bouts and state(bouts[-1]) != "post" else None
        for future in live_details:
            details = future.result()
            fighters = " vs ".join(details["names"].values())
            lines.append(f"  - FIGHTING NOW: {fighters}, round {details['period']}, {details['clock']} on the clock."
                         f"{stats_text(details)}")
        for future in result_details:
            details = future.result()
            if not details or not details["winner"]:
                continue
            loser = next((n for k, n in details["names"].items() if k != details["winner"]), "?")
            method = details["method"] or "decision"
            finish = (f" in round {details['period']}" if details["period"] and "decision" not in method.lower() else "")
            lines.append(f"  - Result: {details['names'].get(details['winner'])} beat {loser} by {method}{finish}.")
        if coming and (live or finished):
            # Only once the card is under way; before it, the first three are
            # just the early prelims, which is not what "what's next" means.
            lines.append("  - Still to come: " + "; ".join(names(b) for b in coming[:3]) + ".")
        if main is not None and main.result() and main.result().get("odds"):
            lines.append(f"  - Main event {names(bouts[-1])}.{odds_text(main.result())}")
    return lines


def fighter_report(item: dict) -> str:
    fighter = re.search(r"~a:(\d+)", item.get("uid", ""))
    if item.get("sport") != "mma" or not fighter:
        return ""
    fighter_id = fighter.group(1)
    with ThreadPoolExecutor(max_workers=3) as pool:
        profile = pool.submit(_get, f"{API}/common/v3/sports/mma/athletes/{fighter_id}")
        records = pool.submit(_get, f"{CORE}/athletes/{fighter_id}/records")
        log = pool.submit(_get, f"{CORE}/athletes/{fighter_id}/eventlog")
        athlete = profile.result().get("athlete") or {}
        record = next((r.get("displayValue") for r in records.result().get("items", [])
                       if r.get("type") == "total"), None)
        entries = (log.result().get("events") or {}).get("items") or []
    name = athlete.get("displayName") or item.get("displayName")
    nickname = f" \"{athlete['nickname']}\"" if athlete.get("nickname") else ""
    division = (athlete.get("weightClass") or {}).get("text")
    lines = [f"{name}{nickname}" + (f", {division}" if division else "") + (f", record {record} (W-L-D)" if record else "")]
    upcoming = [e for e in entries if not e.get("played")]
    played = [e for e in entries if e.get("played")]      # newest first
    if upcoming:
        lines.append("- Next fight: " + fight_line(upcoming[-1], fighter_id))
    if played:
        lines.append("- Last fight: " + fight_line(played[0], fighter_id))
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
        report = fighter_report(item)
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
