"""Alfred's private wording, loaded from files the public repository does not carry.

The character is the project, and it stays private: who he is (persona/alfred.md),
how he talks (persona/examples.md), and the instructions that travel with every
turn (persona/prompts.json). All three are git-ignored. A checkout without them
runs on the .example versions beside them, which show the shape of each file
with a stand-in character.
"""

import json
from pathlib import Path

PERSONA_DIR = Path(__file__).resolve().parent.parent / "persona"


def private_or_example(name: str) -> Path:
    """persona/<name> if it exists here, otherwise persona/<stem>.example<suffix>."""
    private = PERSONA_DIR / name
    if private.exists():
        return private
    return private.with_name(f"{private.stem}.example{private.suffix}")


_PROMPTS = json.loads(private_or_example("prompts.json").read_text(encoding="utf-8"))


def get(key: str):
    return _PROMPTS[key]
