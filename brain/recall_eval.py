#!/usr/bin/env python3
"""Where to set the bar for recall he was never asked for.

A deliberate search ("what did I tell you about X") can afford a loose match: he
went looking, and a near-miss costs him one line. Recall on an ordinary sentence
is different — it arrives unasked in front of every turn, so a loose match is
noise he may repeat back, while a miss only leaves him answering as he would
have anyway. That asymmetry says the bar belongs higher, and this says where.

Memories and probes here are invented, not the owner's own, so this can live in
the repository: what is being measured is the embedder's geometry, not him.

    python3 brain/recall_eval.py              # the table
    python3 brain/recall_eval.py --verbose    # every probe's best match
"""

import argparse
import sys
import tempfile
from pathlib import Path

from memory import Memory

# What he would have been told over the past weeks, one line each.
PAST = [
    "i just ordered a second spool of matte black petg",
    "my espresso machine started leaking from the group head",
    "i signed up for a half marathon in november",
    "the landlord finally fixed the radiator in the front room",
    "im teaching myself bass guitar and slap technique is brutal",
    "my laptop fan died and the thing throttles constantly now",
    "i adopted a rescue greyhound called biscuit",
    "i started a sourdough starter last week",
    "my brother is visiting from seattle in october",
    "i switched to decaf after two in the afternoon",
    "the tomato plants on the balcony got blight",
    "im rebuilding the shed roof this summer",
]

# (what he says now, the line above it should bring back or None for nothing).
PROBES = [
    ("the spool still hasnt turned up", "petg"),
    ("should i descale the espresso machine or is that a different problem", "espresso"),
    ("i managed eight miles this morning without stopping", "half marathon"),
    ("biscuit chewed through another lead today", "greyhound"),
    ("the starter smells like acetone, is that normal", "sourdough"),
    ("when does my brother land", "seattle"),
    ("the blight has spread to the second plant", "blight"),
    ("the radiator is making a knocking sound again", "radiator"),
    ("my fingers are shredded from practising", "bass guitar"),
    ("the laptop is loud again under any load", "laptop fan"),
    # Nothing in the past relates to these. Anything returned is noise.
    ("whats the capital of norway", None),
    ("how long should i boil an egg", None),
    ("what time is it in tokyo", None),
    ("explain how a transformer works", None),
    ("my knee hurts after squats", None),
    ("whats a good film for tonight", None),
    ("how do i get a wine stain out of a shirt", None),
    ("is it going to rain tomorrow", None),
]

FLOORS = (0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.70)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--limit", type=int, default=2)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as folder:
        memory = Memory(Path(folder) / "recall-eval.sqlite3")
        for line in PAST:
            memory.record(line, "Noted.")
        if memory.db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] < len(PAST):
            sys.exit("The embedder is unreachable, so similarity cannot be measured.")

        scored = []
        for prompt, expected in PROBES:
            hits = memory.search(prompt, limit=args.limit, skip_recent=0, floor=0.0)
            scored.append((prompt, expected, hits))
            if args.verbose:
                best = f"{hits[0]['score']:.3f} {hits[0]['user']}" if hits else "nothing"
                print(f"  {prompt[:44]:<46} {best}")

        print(f"\n  {len(PROBES)} probes, {len(PAST)} remembered lines, top {args.limit} kept")
        print("  floor   found   wrong   silent   noise")
        for floor in FLOORS:
            found = wrong = silent = noise = 0
            for prompt, expected, hits in scored:
                kept = [hit for hit in hits if hit["score"] >= floor]
                if expected is None:
                    noise += len(kept)
                elif not kept:
                    silent += 1
                elif any(word in kept[0]["user"] for word in expected.split()):
                    found += 1
                else:
                    wrong += 1
            wanted = sum(1 for _, expected, _ in scored if expected is not None)
            print(f"  {floor:.2f}    {found:>2}/{wanted}   {wrong:>5}   {silent:>6}   {noise:>5}")
        print("\n  found: the right line came back. wrong: something else came back first.")
        print("  silent: nothing came back when something should have.")
        print("  noise: lines returned for probes that relate to nothing (lower is better).")
        memory.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
