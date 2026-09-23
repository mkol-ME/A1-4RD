"""Tools that live outside the repository, loaded from the array at start-up.

Some of what Alfred can do belongs to his owner rather than to the public
project: the code, the data and sometimes the fact that the feature exists at
all are kept on the storage array beside the persona and the memory, for the
same reasons. This module is the single place they attach. It names none of
them and knows nothing about them - it looks in a directory, loads what is there
that has the right shape, and offers their schemas to the decider alongside the
built-in tools.

A fresh clone has no such directory, so no private tools, and behaves exactly
as it did before this module existed.

A private tool module provides:

    TOOLS                               Ollama tool schemas, shaped like memory_tools.TOOLS
    dispatch(name, arguments, prompt)   -> dict with at least "ok"

`prompt` is the owner's own message for the turn, verbatim. A tool that acts on
what was asked should read it from there rather than from arguments the decider
wrote: the decider paraphrases, is capped at a few dozen tokens, and is exactly
the thing a sentence in a search result would try to steer.

Besides "ok", the result may carry:

    "report"   text for the answerer, framed by the tool that produced it
    "direct"   text to be spoken exactly as written, with no answerer at all

"direct" is for answers whose wording is the answer - a list meant to be read
out in order, which a model would shorten, merge or reorder in the retelling.

A module that fails to load, or a dispatch that raises, costs that one tool and
never the turn. Alfred with a broken private tool is still Alfred.
"""

import importlib.util
import os
import sys
from pathlib import Path

DIRECTORY = Path(os.environ.get("ALFRED_PRIVATE_TOOLS") or "/srv/storage/alfred/private/tools")


class Registry:
    def __init__(self, directory: Path, reserved=()):
        self.modules = {}          # tool name -> the module that serves it
        self.problems = []         # (file, reason), for the start-up log
        if not directory.is_dir():
            return
        for path in sorted(directory.glob("*.py")):
            try:
                spec = importlib.util.spec_from_file_location(f"private_tool_{path.stem}", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                schemas = list(getattr(module, "TOOLS", []))
                if not callable(getattr(module, "dispatch", None)):
                    raise TypeError("no dispatch()")
            except Exception as exc:
                self.problems.append((path.name, f"{type(exc).__name__}: {exc}"))
                continue
            for schema in schemas:
                name = schema.get("function", {}).get("name")
                # A private tool may never take over a built-in one: the
                # built-ins are the ones whose behaviour has been measured.
                if not name or name in reserved or name in self.modules:
                    self.problems.append((path.name, f"tool name {name!r} refused"))
                    continue
                self.modules[name] = (module, schema)

    def schemas(self) -> list:
        return [schema for _, schema in self.modules.values()]

    def owns(self, name: str) -> bool:
        return name in self.modules

    def dispatch(self, name: str, arguments: dict, prompt: str) -> dict:
        module, _ = self.modules[name]
        try:
            result = module.dispatch(name, arguments, prompt)
        except Exception as exc:
            return {"ok": False, "error": f"{name} failed: {exc}"}
        if not isinstance(result, dict):
            return {"ok": False, "error": f"{name} returned {type(result).__name__}, not a dict"}
        return result


def load(reserved=()) -> Registry:
    registry = Registry(DIRECTORY, reserved)
    for file, reason in registry.problems:
        print(f"private tool {file} skipped: {reason}", file=sys.stderr, flush=True)
    return registry
