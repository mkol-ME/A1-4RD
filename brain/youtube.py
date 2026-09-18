"""What a YouTube channel has posted lately, by the name the owner calls it.

Only the MMA Guru was wired in, by channel id. Asked for "Money Manzell MMA's
latest post" or "Bedtime MMA's UFC 331 predictions", the decider fell back to
web search, which missed Bedtime MMA's "UFC 331 Full Card Predictions" the day
it went up and read out titles nobody could confirm (2026-09-17). This reads the
channel's real upload list instead, so every title he says is one YouTube gave.

Names arrive through Whisper, spelled however it heard them ("Money Manzell"
for "Money Manzel MMA"), so the channel is picked by how close the name is,
with follower count only breaking near-ties between namesakes.
"""

import difflib
import json
import math
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import prompts

MEDIA_URL = os.environ.get("ALFRED_MEDIA_URL", "http://127.0.0.1:5053").rstrip("/")
TIMEOUT = 30
UPLOADS_READ = 15
LATEST_SPOKEN = 5
DATED = 3             # uploads whose date is fetched; each is a separate page
MIN_NAME_MATCH = 0.6


def plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text.lower().replace("'", "")))


def squash(text: str) -> str:
    return plain(text).replace(" ", "")


def best_channel(asked: str, channels: list[dict]) -> dict | None:
    """The channel whose name is closest to what was said; None if none is close.

    "the mma guru" must not lose to a namesake with a hundredth of the followers,
    and "money manzell mma" must still find "Money Manzel MMA".
    """
    wanted = squash(re.sub(r"\b(?:the|youtube|channel|on youtube)\b", " ", plain(asked)))
    best, best_score = None, 0.0
    for channel in channels:
        name = squash(channel.get("name") or "")
        if not name or not wanted:
            continue
        closeness = difflib.SequenceMatcher(None, wanted, name).ratio()
        if wanted in name or name in wanted:
            closeness = max(closeness, 0.9)
        if closeness < MIN_NAME_MATCH:
            continue
        # "lucas tracy" is also the exact name of a one-follower channel; LucasTracyMMA
        # has 168,000. A name that merely contains his words should still win on that.
        score = closeness + 0.05 * math.log10((channel.get("followers") or 0) + 1)
        if score > best_score:
            best, best_score = channel, score
    return best


def matching(uploads: list[dict], topic: str) -> list[dict]:
    """Uploads whose titles carry the topic's words, best match first, newest first among equals.

    A number in the topic must be there exactly: "ufc 331" is not "ufc 330".
    """
    words = [w for w in plain(topic).split() if len(w) > 1 and w not in {"the", "and", "for", "video", "videos",
                                                                          "post", "posts", "latest", "new"}]
    numbers = [w for w in words if w.isdigit()]
    scored = []
    for position, upload in enumerate(uploads):
        title = set(plain(upload.get("title") or "").split())
        if any(n not in title for n in numbers):
            continue
        overlap = sum(1 for w in words if w in title)
        if overlap:
            scored.append((-overlap, position, upload))
    return [upload for _, _, upload in sorted(scored, key=lambda item: item[:2])]


def _get(path: str, **params) -> dict:
    url = f"{MEDIA_URL}{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        payload = json.loads(response.read())
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload


def _posted(video_id: str) -> str | None:
    try:
        date = _get("/video", id=video_id).get("upload_date") or ""
    except Exception:
        return None
    return f"{date[4:6]}/{date[6:8]}/{date[:4]}" if len(date) == 8 else None


def _line(number: int, upload: dict, posted: dict) -> str:
    when = posted.get(upload["id"])
    return f'{number}. "{upload["title"]}"' + (f" (posted {when})" if when else "")


def lookup(channel: str, topic: str | None = None) -> dict:
    try:
        found = best_channel(channel, _get("/find_channel", q=channel)["channels"])
        if found is None:
            return {"ok": True, "found": 0, "note": f"No YouTube channel called anything like '{channel}' "
                                                    f"turned up. Tell {prompts.OWNER} so; do not guess one."}
        uploads = _get("/channel", id=found["id"], n=UPLOADS_READ)["uploads"]
    except Exception as exc:
        return {"ok": False, "found": 0, "note": f"YouTube could not be reached ({exc}). Say so."}
    if not uploads:
        return {"ok": True, "found": 0, "note": f"{found['name']} has no uploads listed."}

    hits = matching(uploads, topic) if topic else []
    shown = hits[:LATEST_SPOKEN] if topic else uploads[:LATEST_SPOKEN]
    with ThreadPoolExecutor(max_workers=DATED) as pool:
        dates = dict(zip([u["id"] for u in shown[:DATED]], pool.map(_posted, [u["id"] for u in shown[:DATED]])))

    lines = [f"YouTube channel {found['name']}, read from its real upload list just now."]
    if topic:
        if hits:
            lines.append(f"Its uploads about '{topic}', best match first:")
            lines += [_line(i, u, dates) for i, u in enumerate(shown, 1)]
        else:
            lines.append(f"None of its latest {len(uploads)} uploads mention '{topic}'. Its newest are:")
            lines += [_line(i, u, {}) for i, u in enumerate(uploads[:3], 1)]
    else:
        lines.append("Its newest uploads, newest first:")
        lines += [_line(i, u, dates) for i, u in enumerate(shown, 1)]
    lines.append("Give titles exactly as written here and never invent one. If he asked for the latest, "
                 "that is number 1.")
    return {"ok": True, "found": len(hits) if topic else len(shown), "report": "\n".join(lines),
            "channel": found["name"], "videos": shown}


if __name__ == "__main__":
    import sys
    result = lookup(sys.argv[1] if len(sys.argv) > 1 else "bedtime mma", sys.argv[2] if len(sys.argv) > 2 else None)
    print(result.get("report") or result)
