"""Alfred's private wording, loaded from files the public repository does not carry.

The character is the project, and it stays private: who he is (persona/alfred.md),
how he talks (persona/examples.md), and the instructions that travel with every
turn (persona/prompts.json). All three are git-ignored. A checkout without them
runs on the .example versions beside them, which show the shape of each file
with a stand-in character.
"""

import json
import os
import random
from pathlib import Path

# Where the stand-ins live: always the checkout, so a fresh clone runs.
EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "persona"
# Where the real wording lives. It does not have to be in the checkout, and on
# the server it is not: ALFRED_PERSONA_DIR points at the storage array, beside
# the memory database, so nothing private sits in the repository folder at all.
PERSONA_DIR = Path(os.environ.get("ALFRED_PERSONA_DIR") or EXAMPLE_DIR)


def private_or_example(name: str) -> Path:
    """The private file if it exists, otherwise the stand-in in the checkout."""
    private = PERSONA_DIR / name
    if private.exists():
        return private
    stem, suffix = Path(name).stem, Path(name).suffix
    return EXAMPLE_DIR / f"{stem}.example{suffix}"


_PROMPTS = json.loads(private_or_example("prompts.json").read_text(encoding="utf-8"))


def get(key: str):
    return _PROMPTS[key]


# What he calls the person he works for. A real first name is personal, so it
# lives with the rest of the private wording; the .example file says "the user".
OWNER = _PROMPTS["owner_name"]

# His fixed lines: the ones said the same way every time, in each language he
# speaks. They are his voice, so they live here rather than in the code.
LINES = _PROMPTS["lines"]

# English line -> the Brazilian Portuguese he says instead, for the turns that
# pick a line in English and only then learn which language is being spoken.
TRANSLATIONS = {entry["en"]: entry["pt"] for entry in LINES.values()
                if isinstance(entry.get("en"), str) and isinstance(entry.get("pt"), str)}


def line(key: str, language: str = "en", **fields) -> str:
    """One fixed line, in the language of the turn, with any blanks filled."""
    value = LINES[key].get(language) or LINES[key]["en"]
    if isinstance(value, list):
        value = random.choice(value)
    return value.format(**fields) if fields else value
