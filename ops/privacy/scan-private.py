#!/usr/bin/env python3
"""Refuse to push anything of his that is meant to stay off the internet.

The private files are the needles: whatever is in the wording, the examples and
the local lists is, by definition, what must not appear in a commit. The scan
reads them wherever they live — the checkout, or ALFRED_PERSONA_DIR on the
array — and looks for them in the tracked tree and in commit messages.

A hit is not a dead end. The rule is to commit a censored version and keep the
real one on the server: put the wording behind persona/prompts.json and a
stand-in in prompts.example.json, as brain/prompts.py already does.

    python3 ops/privacy/scan-private.py              # tracked tree + unpushed messages
    python3 ops/privacy/scan-private.py --range A..B # a specific commit range
    python3 ops/privacy/scan-private.py --install    # add the pre-push hook

Exit status is 1 if anything was found, so a hook can stop the push.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MIN_PHRASE = 25          # shorter than this and ordinary English starts matching


def run(*args: str) -> str:
    done = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, errors="replace")
    return done.stdout


def persona_dir() -> Path:
    import os
    return Path(os.environ.get("ALFRED_PERSONA_DIR") or ROOT / "persona")


def read_private(name: str) -> str | None:
    """The private file, from wherever it is kept.

    The wording is not supposed to sit on this machine at all, so when it is
    not here the scan asks the server for it over ssh and keeps it in memory.
    Without either, there is nothing to check against and the push is refused
    rather than waved through.
    """
    local = persona_dir() / name
    if local.exists():
        return local.read_text(encoding="utf-8")
    import os
    host = os.environ.get("ALFRED_HOST", "a1-4rd")
    done = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", host,
                           f"cat /srv/storage/alfred/persona/{name}"],
                          capture_output=True, text=True, errors="replace")
    return done.stdout if done.returncode == 0 and done.stdout.strip() else None


def needles() -> dict[str, set[str]]:
    """What to look for, grouped by what it is, from the private files themselves."""
    found: dict[str, set[str]] = {}

    def add(label: str, value: str) -> None:
        value = value.strip()
        if value:
            found.setdefault(label, set()).add(value)

    raw = read_private("prompts.json")
    if raw:
        data = json.loads(raw)
        if isinstance(data.get("owner_name"), str):
            add("the owner's name", data["owner_name"])
        for key, value in data.items():
            if key == "owner_name":
                continue
            for text in re.findall(r'"([^"]+)"|\'([^\']+)\'', json.dumps(value, ensure_ascii=False)):
                phrase = (text[0] or text[1]).strip()
                if len(phrase) >= MIN_PHRASE and not phrase.startswith("{"):
                    add("private prompt wording", phrase)

    for name, label in (("alfred.md", "persona wording"), ("examples.md", "a real example exchange")):
        text = read_private(name)
        if not text:
            continue
        for line_ in text.splitlines():
            phrase = line_.strip().lstrip("#-* MA:").strip()
            if len(phrase) >= MIN_PHRASE:
                add(label, phrase)

    for name, label in (("people.local.txt", "a real person's name"),
                        ("location.local.txt", "where he lives"),
                        ("vocabulary.local.txt", "a personal place or school")):
        text = read_private(name)
        if not text:
            continue
        for token in re.split(r"[\s,]+", text):
            if len(token.strip()) >= 4:
                add(label, token.strip())

    # Subjects that are to have no presence here at all, one per line. Read
    # whole rather than split into tokens, and with no length floor: the point
    # is to catch a short name wherever it appears, and a false stop costs one
    # look while a miss costs a push that cannot be taken back. Comments and
    # blank lines are skipped so the file can say what it is for.
    text = read_private("topics.local.txt")
    for line_ in (text or "").splitlines():
        phrase = line_.strip()
        if phrase and not phrase.startswith("#"):
            add("a private subject", phrase)

    return found


PATTERNS = [
    ("a private address", re.compile(r"\b(?:192\.168|10\.\d{1,3})\.\d{1,3}\.\d{1,3}\b")),
    ("an email address", re.compile(r"\b[\w.%+-]+@(?!(?:users\.)?noreply\.[\w.-]+|example\.com)[\w.-]+\.\w{2,}\b")),
    ("a laptop path", re.compile(r"[Cc]:\\Users\\[A-Za-z0-9._-]+")),
    ("the server account", re.compile(r"/home/[a-z][a-z0-9_-]*")),
    ("a credential", re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{16,}|AIza[A-Za-z0-9_-]{20,})")),
]


# Addresses that are meant to be public: the noreply ones commits are signed
# with, and anything obviously made up in an example.
ALLOWED_EMAILS = ("users.noreply.github.com", "noreply@anthropic.com", "@example.com", "@example.org")


def tracked_files() -> list[str]:
    return [line for line in run("git", "ls-files").splitlines() if line]


def scan_text(text: str, where: str, marks: dict[str, set[str]], hits: list[tuple[str, str, str]]) -> None:
    lowered = text.lower()
    for label, values in marks.items():
        for value in values:
            if value.lower() in lowered:
                hits.append((where, label, value))
    for label, pattern in PATTERNS:
        for match in pattern.findall(text):
            value = match if isinstance(match, str) else match[0]
            if label == "an email address" and any(ok in value for ok in ALLOWED_EMAILS):
                continue
            hits.append((where, label, value))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--range", help="commit range whose messages to read, e.g. origin/main..HEAD")
    parser.add_argument("--install", action="store_true", help="write .git/hooks/pre-push and exit")
    args = parser.parse_args()

    if args.install:
        hook = ROOT / ".git" / "hooks" / "pre-push"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text('#!/bin/sh\nexec python "$(git rev-parse --show-toplevel)/ops/privacy/scan-private.py"\n',
                        encoding="utf-8", newline="\n")
        hook.chmod(0o755)
        print(f"pre-push hook written to {hook}")
        return 0

    marks = needles()
    if not marks:
        print("Nothing to check against: no private files here and the server did not answer.\n"
              "The scan refuses rather than passes a push it could not inspect.", file=sys.stderr)
        return 1

    hits: list[tuple[str, str, str]] = []
    for name in tracked_files():
        path = ROOT / name
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scan_text(text, name, marks, hits)

    commits = args.range or "origin/main..HEAD"
    messages = run("git", "log", commits, "--format=%H%n%B")
    if messages.strip():
        scan_text(messages, f"a commit message in {commits}", marks, hits)

    total = sum(len(v) for v in marks.values())
    if not hits:
        print(f"clean: {len(tracked_files())} tracked files and the messages in {commits}, "
              f"checked against {total} private phrases")
        return 0

    print(f"STOP: private material would be pushed ({len(hits)} occurrences)\n")
    seen = set()
    for where, label, value in hits:
        key = (where, label, value[:40])
        if key in seen:
            continue
        seen.add(key)
        shown = value if len(value) <= 40 else value[:37] + "..."
        print(f"  {where}\n      {label}: {shown!r}")
    print("\nCommit a censored version and keep the real wording on the server:")
    print("  /srv/storage/alfred/persona   his wording, read through brain/prompts.py")
    print("  /srv/storage/alfred/private   evals and design notes")
    return 1


if __name__ == "__main__":
    sys.exit(main())
