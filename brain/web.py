"""Searching the web, for the one problem persona work cannot touch.

He states wrong numbers with total confidence — "set retraction to about three
millimetres per second" when the real range is 25 to 45. Examples teach voice,
not facts, so the only fix is a source he can check.

General search runs through SearXNG on the box itself. Scraping DuckDuckGo
directly worked for about a dozen requests and then began serving a CAPTCHA
page asking us to identify ducks; the hosted APIs all want an account, and the
one advertised as free wanted a card on file. A local aggregator has no account
to lose, no key to rotate, no free tier to be withdrawn, and rotates upstream
engines itself — which is the part the hand-rolled scraper could not do.

Wikipedia is queried alongside it and needs nothing at all, so if SearXNG is
down Alfred still answers encyclopedic questions and says he does not know on
the rest, which is the entire point of this module.

Snippets only, never whole pages: the less attacker-controlled text reaches the
prompt the better, and a full page is mostly text nobody asked for.

Everything here is untrusted. It is text written by strangers, arriving inside
a prompt, and the model has already demonstrated this week that it will follow
whatever is nearest. So results are labelled as quoted material at the point of
use (see memory_tools), are never written to memory as facts, and are stripped
of anything that looks like an instruction before they get that far.
"""

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

import os

TIMEOUT = 12
# Local, so it can be generous with itself; the aggregator is doing several
# upstream requests behind this one.
SEARX_URL = os.environ.get("ALFRED_SEARX_URL", "http://127.0.0.1:8888").rstrip("/")
SEARX_TIMEOUT = int(os.environ.get("ALFRED_SEARX_TIMEOUT", "20"))
BRAVE_KEY = os.environ.get("BRAVE_API_KEY", "").strip()
MAX_RESULTS = 4
MAX_SNIPPET_CHARS = 320
# A desktop string, because the lite endpoint serves a near-empty page to
# anything that looks automated.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}

# Phrases whose only purpose in a search result is to talk to a language model.
# Not a security boundary — a determined page can evade any list of words — but
# it removes the lazy attempts, and what survives is still labelled as a quote
# rather than as instruction.
INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above)|disregard (the |all )?(previous|prior)"
    r"|you are now|new instructions?|system prompt|act as|pretend to be"
    r"|forget (everything|your)|</?(system|assistant|user)>)",
    re.I,
)


class _Snippets(HTMLParser):
    """Pull result titles, links and snippets out of the DuckDuckGo lite page.

    Written against the markup rather than a library: the RVC environment is
    pinned hard and adding a parser to it for this would be a poor trade.
    """

    def __init__(self):
        super().__init__()
        self.results, self._current, self._collect = [], None, None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "")
        if tag == "a" and "result-link" in classes:
            self._current = {"title": "", "url": attributes.get("href", ""), "snippet": ""}
            self._collect = "title"
        elif tag == "td" and "result-snippet" in classes:
            self._collect = "snippet"

    def handle_endtag(self, tag):
        if tag == "a" and self._collect == "title":
            self._collect = None
        elif tag == "td" and self._collect == "snippet":
            self._collect = None
            if self._current:
                self.results.append(self._current)
                self._current = None

    def handle_data(self, data):
        if self._current and self._collect:
            self._current[self._collect] += data


def _get(url, data=None):
    request = urllib.request.Request(url, data=data, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


def _clean(text):
    text = html.unescape(re.sub(r"\s+", " ", text or "")).strip()
    text = INJECTION.sub("[removed]", text)
    return text[:MAX_SNIPPET_CHARS].strip()


def _real_url(link):
    """DuckDuckGo wraps results in a redirect; the real one is in the query."""
    if "duckduckgo.com/l/" in link or link.startswith("//duckduckgo.com/l/"):
        query = urllib.parse.urlparse("https:" + link if link.startswith("//") else link).query
        target = urllib.parse.parse_qs(query).get("uddg")
        if target:
            return target[0]
    return link


def wikipedia(query):
    """The lead paragraph of the closest article, or None."""
    try:
        found = json.loads(_get(
            "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
                "action": "query", "list": "search", "srsearch": query,
                "srlimit": 1, "format": "json"})))
        hits = found.get("query", {}).get("search", [])
        if not hits:
            return None
        title = hits[0]["title"]
        page = json.loads(_get("https://en.wikipedia.org/api/rest_v1/page/summary/"
                               + urllib.parse.quote(title.replace(" ", "_"))))
        extract = _clean(page.get("extract", ""))
        if not extract:
            return None
        return {"title": _clean(page.get("title", title)), "snippet": extract,
                "url": page.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "source": "wikipedia"}
    except Exception:
        return None


class Blocked(Exception):
    """The engine served a challenge page instead of results."""


def duckduckgo(query, limit=MAX_RESULTS):
    try:
        page = _get("https://lite.duckduckgo.com/lite/",
                    urllib.parse.urlencode({"q": query}).encode())
    except Exception:
        return []
    if "challenge" in page.lower() or "confirm this search was made by a human" in page.lower():
        raise Blocked("DuckDuckGo is asking for a CAPTCHA")
    parser = _Snippets()
    parser.feed(page)
    results = []
    for item in parser.results:
        snippet = _clean(item["snippet"])
        title = _clean(item["title"])
        if not snippet or not title:
            continue
        results.append({"title": title, "snippet": snippet,
                        "url": _real_url(item["url"]), "source": "duckduckgo"})
        if len(results) >= limit:
            break
    return results


def brave(query, limit=MAX_RESULTS):
    """Brave's search API. Free tier, no card, but it does want an account."""
    if not BRAVE_KEY:
        return []
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": query, "count": limit})
    request = urllib.request.Request(url, headers={
        "Accept": "application/json", "X-Subscription-Token": BRAVE_KEY})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise Blocked(f"Brave returned {error.code}") from error
    except Exception:
        return []
    results = []
    for item in payload.get("web", {}).get("results", [])[:limit]:
        snippet = _clean(item.get("description", ""))
        title = _clean(item.get("title", ""))
        if snippet and title:
            results.append({"title": title, "snippet": snippet,
                            "url": item.get("url", ""), "source": "brave"})
    return results


def searxng(query, limit=MAX_RESULTS):
    """Ask the local aggregator, which asks several engines and merges them."""
    url = f"{SEARX_URL}/search?" + urllib.parse.urlencode({
        "q": query, "format": "json", "language": "en", "safesearch": "0"})
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=SEARX_TIMEOUT) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        # 403 here almost always means the JSON format is not enabled in
        # settings.yml, which is a configuration problem worth naming.
        raise Blocked(f"SearXNG returned {error.code}"
                      f"{' — is json in search.formats?' if error.code == 403 else ''}") from error
    except Exception as error:
        raise Blocked(f"SearXNG unreachable at {SEARX_URL} ({type(error).__name__})") from error

    results = []
    for item in payload.get("results", [])[:limit * 2]:
        snippet = _clean(item.get("content", ""))
        title = _clean(item.get("title", ""))
        if not snippet or not title:
            continue
        results.append({"title": title, "snippet": snippet,
                        "url": item.get("url", ""), "source": "searxng"})
        if len(results) >= limit:
            break
    return results


def search(query, limit=MAX_RESULTS):
    """Wikipedia first where it has an article, then general results.

    Wikipedia leads because the questions this exists for are factual, and a
    lead paragraph is a better answer to "how fast should retraction be" than
    the first forum thread about it.
    """
    query = " ".join(str(query).split())[:200]
    results, problems = [], []
    general = brave if BRAVE_KEY else searxng
    keywords = _keywords(query)

    # All three lookups go out at once. Run in series they were the whole of a
    # searched turn's silence — 0.6s to 3.4s, while SearXNG alone answers in
    # 0.3s — and every one of them is waiting on someone else's server, not on
    # this machine. The keyword retry is sent whether or not it turns out to be
    # needed; a spare Wikipedia request is cheaper than a second round trip.
    with ThreadPoolExecutor(max_workers=3) as pool:
        by_question = pool.submit(wikipedia, query)
        # Wikipedia's search is sensitive to how a question is phrased, and the
        # model phrases things as questions. Try again on the nouns alone.
        by_keywords = pool.submit(wikipedia, keywords) if keywords != query else None
        general_results = pool.submit(general, query, limit)

        article = _relevant(query, by_question.result())
        if not article and by_keywords is not None:
            article = _relevant(query, by_keywords.result())
        if article:
            results.append(article)
        try:
            for item in general_results.result():
                if len(results) >= limit:
                    break
                results.append(item)
        except Blocked as blocked:
            problems.append(str(blocked))

    return {"results": results, "problems": problems}


FILLER = re.compile(
    r"^\s*(what(?:'?s| is| are)?|how (?:many|much|do i|long)|whats|which|who|when|where|why)\b"
    r"|\b(a|an|the|good|best|proper|correct|recommended|for|should|i|my|to|of)\b", re.I)


def _relevant(query, article):
    """Drop an article that shares no real words with the question.

    Wikipedia always returns its closest match, which for "how many feet are in
    a mile" was the article on the gram. An unrelated encyclopedia entry quoted
    as an answer is worse than no answer at all.
    """
    if not article:
        return None
    wanted = {w for w in re.findall(r"[a-z]{4,}", _keywords(query).lower())}
    if not wanted:
        return article
    haystack = (article["title"] + " " + article["snippet"]).lower()
    return article if any(w in haystack for w in wanted) else None


def _keywords(query):
    """The question stripped back to its nouns, for a keyword-shaped index."""
    return " ".join(FILLER.sub(" ", query).split()) or query


if __name__ == "__main__":
    import sys
    found = search(" ".join(sys.argv[1:]) or "retraction speed for petg")
    for problem in found["problems"]:
        print(f"  ! {problem}")
    for result in found["results"]:
        print(f"[{result['source']}] {result['title']}\n  {result['snippet']}\n  {result['url']}\n")
