"""Live odds from Polymarket's prediction markets.

"Who's favoured on Saturday" and "what are the chances the Fed hikes" have no
checkable answer, only a price. Polymarket's public Gamma API serves those
prices for sport, politics and economics without an account or a key, in
0.3-0.5s, and they move within minutes of trading.

Read-only: nothing here places, suggests or sizes a bet. A price is what
traders are paying, not a fact about the future, and the text handed to the
answerer says so.
"""

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import sports

GAMMA = "https://gamma-api.polymarket.com"
TIMEOUT = 8
MAX_EVENTS = 2
MAX_MARKETS = 5
# Markets this thin are one trader's opinion; skipped unless nothing else matches.
MIN_VOLUME = 10000.0
DATED = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|\b20\d\d\b", re.I)
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
STOP = {"the", "what", "whats", "are", "odds", "chances", "chance", "for", "who", "will", "win",
        "polymarket", "market", "betting", "favored", "favorite", "and", "vs", "versus"}


def date_order(label: str) -> tuple:
    year = re.search(r"\b(20\d\d)\b", label)
    month = next((i for i, m in enumerate(MONTHS) if re.search(rf"\b{m}", label, re.I)), 0)
    return (int(year.group(1)) if year else 0, month)


def _get(url: str):
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "alfred/1.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())


def _list(value) -> list:
    """Gamma sends outcomes and prices as JSON strings inside the JSON."""
    if isinstance(value, list):
        return value
    try:
        return json.loads(value or "[]")
    except (TypeError, ValueError):
        return []


def price(market: dict) -> list[float]:
    """Each outcome's price, from the order book midpoint when there is a real one."""
    prices = [float(p) for p in _list(market.get("outcomePrices"))]
    bid, ask = market.get("bestBid"), market.get("bestAsk")
    if len(prices) == 2 and bid is not None and ask is not None and float(ask) - float(bid) <= 0.1:
        middle = (float(bid) + float(ask)) / 2
        prices = [middle, 1 - middle]
    return prices


def percent(value: float) -> str:
    share = value * 100
    if share < 1:
        return "under 1%"
    if share > 99:
        return "over 99%"
    return f"{share:.0f}%"


def live(market: dict) -> bool:
    """Open and actually traded. An archived duplicate of the RFK Jr. nominee
    market, never traded, carried a placeholder 49% and read as a coin flip."""
    return (market.get("active") and not market.get("closed") and not market.get("archived")
            and (market.get("lastTradePrice") is not None or market.get("bestBid") is not None))


def describe_event(event: dict) -> list[str]:
    markets = [m for m in event.get("markets") or [] if live(m)]
    if not markets:
        return []
    lines = [f"{event.get('title')} (${float(event.get('volume') or 0):,.0f} traded):"]
    yes_no = all([o.lower() for o in _list(m.get("outcomes"))] == ["yes", "no"] for m in markets)
    if yes_no and len(markets) > 1:
        # "Who will be champion": one yes/no market per candidate, best first.
        # "Rate cut by…" is a ladder of dates and keeps its own order.
        dated = all(DATED.search(m.get("groupItemTitle") or "") for m in markets)
        ranked = (sorted(markets, key=lambda m: date_order(m.get("groupItemTitle") or "")) if dated
                  else sorted(markets, key=lambda m: (price(m) or [0])[0], reverse=True))
        for market in ranked[:MAX_MARKETS]:
            label = market.get("groupItemTitle") or market.get("question")
            lines.append(f"- {label}: {percent(price(market)[0])}")
        return lines
    for market in markets[:MAX_MARKETS]:
        outcomes, prices = _list(market.get("outcomes")), price(market)
        if len(outcomes) != len(prices) or not outcomes:
            continue
        if [o.lower() for o in outcomes] == ["yes", "no"]:
            lines.append(f"- {market.get('question')}: yes {percent(prices[0])}")
        else:
            pairs = ", ".join(f"{o} {percent(p)}" for o, p in zip(outcomes, prices))
            lines.append(f"- {market.get('question')}: {pairs}")
    return lines


def _words(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def rank(events: list[dict], wanted: set) -> list[dict]:
    """Search hits, most relevant first, with anything unrelated dropped."""
    liquid = [e for e in events if float(e.get("volume") or 0) >= MIN_VOLUME] or events

    def named(event):
        name = " ".join([event.get("title") or ""] + [t.get("label") or "" for t in event.get("tags") or []])
        return len(wanted & _words(name)) / len(wanted) if wanted else 0.0

    def mentioned(event):
        body = " ".join([event.get("description") or ""] + [m.get("question") or "" for m in event.get("markets") or []])
        return bool(wanted & _words(body))

    volume = lambda e: float(e.get("volume") or 0)
    by_name = sorted((e for e in liquid if named(e) > 0), key=lambda e: (-named(e), -volume(e)))
    if by_name or not wanted:
        return by_name if wanted else sorted(liquid, key=lambda e: -volume(e))
    # A title sharing none of his words is Polymarket's search reaching: "who is
    # favored in the bears game" came back as who dies in The Witcher.
    return sorted((e for e in liquid if mentioned(e)), key=lambda e: -volume(e))


def lookup(query: str) -> dict:
    query = " ".join(str(query).split())[:120]
    data = _get(f"{GAMMA}/public-search?" + urllib.parse.urlencode(
        {"q": query, "limit_per_type": 6, "events_status": "active"}))
    events = [e for e in data.get("events") or [] if e.get("active") and not e.get("closed")]
    # Choosing among the search hits went wrong five different ways while this
    # was written, each fixed rule breaking another case (2026-09-16):
    #   search order: a $2K market on dissenting Fed votes beat the $4.7M decision
    #   volume alone: "bears vikings" became the Super Bowl futures
    #   titles only:  "super bowl" found nothing ("Pro Football: 2027 Champion")
    #   any text:     "pantoja van" became the flyweight-title futures
    # What holds for all of them (tests/test_markets.py): the share of his words
    # in the title and tags — Polymarket tags that market "Super Bowl" — then
    # volume; the description and questions only when no title or tag matches.
    wanted = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2 and w not in STOP}
    ranked = rank(events, wanted)
    chosen = ranked[:MAX_EVENTS]
    lines = []
    for event in chosen:
        lines.extend(describe_event(event))
    if not lines:
        return {"ok": True, "found": 0, "note": f"Polymarket has no open market on '{query}'. Say so."}
    stamp = datetime.now(timezone.utc).astimezone(ZoneInfo(sports.TIMEZONE))
    header = (f"Prediction-market odds from Polymarket, as of {stamp.hour % 12 or 12}:{stamp.minute:02d} "
              f"{stamp.strftime('%p')}. A percentage is what traders are currently paying, not a fact "
              f"about the future; say it as 'the market has…', and never suggest a bet:")
    return {"ok": True, "found": len(chosen), "report": "\n".join([header] + lines)}


if __name__ == "__main__":
    import sys
    result = lookup(" ".join(sys.argv[1:]) or "pantoja van")
    print(result.get("report") or result.get("note"))
