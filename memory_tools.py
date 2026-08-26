"""The memory tools Alfred is allowed to call, and the dispatcher behind them.

Retrieved context is pushed at him on every turn whether it helps or not. These
let him go and look instead, and write something down when it is worth keeping.

Reliability is the whole point of this module, so the dispatcher is strict in
one direction and forgiving in the other: it validates every argument before it
touches the database, and it never raises. A tool call that goes wrong comes
back as a result the model can read and correct itself from, because an
exception here would kill the turn and Alfred would simply stop talking.

Small models get tool arguments slightly wrong in predictable ways — a number
sent as "3", a single string where a list belongs, the key named `text` when the
schema says `query`. Coercing those is not sloppiness; refusing them costs a
whole extra round trip to fix something we already understood.
"""

import json

MAX_FACT_CHARS = 500
MAX_QUERY_CHARS = 500
MAX_RESULTS = 10


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": (
                "Search everything the user and I have said to each other before, by meaning "
                "rather than by keyword. Use it when he refers to something from an earlier "
                "conversation, when he asks what he told me, or when knowing what was said "
                "before would change the answer. Returns nothing when nothing is related "
                "enough, which is a real answer — say so rather than inventing something."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to look for, in plain words. A phrase works better than a keyword.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "How many exchanges to return. Default 3, maximum 10.",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": (
                "Write down one durable fact about the user, his machines, or his preferences — "
                "something that will still be true next month and that I should know without "
                "being told again. Not for passing detail: the conversation is already saved "
                "in full, so this is only for what deserves to be surfaced every time. One "
                "fact per call, stated plainly and in full, because it will be read back "
                "without any of the surrounding conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The fact, as a complete standalone sentence. 'His printer is a Bambu P1S', not 'the P1S'.",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_facts",
            "description": "List every durable fact currently written down, with its id. Use this before forgetting one.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_fact",
            "description": (
                "Delete one durable fact by id, when the user says it is wrong or no longer true. "
                "Look the id up with list_facts first — never guess it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fact_id": {"type": "integer", "description": "The id shown by list_facts."},
                },
                "required": ["fact_id"],
            },
        },
    },
]

TOOL_NAMES = [tool["function"]["name"] for tool in TOOLS]


class ToolError(Exception):
    """A bad call, phrased so the model can fix it and try again."""


def _as_text(arguments: dict, *names: str, limit: int) -> str:
    """Pull a string argument, accepting the names the model actually uses."""
    for name in names:
        if name in arguments and arguments[name] is not None:
            value = arguments[name]
            if isinstance(value, (list, tuple)):     # sent a list of one
                value = " ".join(str(part) for part in value)
            text = " ".join(str(value).split()).strip()
            if not text:
                raise ToolError(f"'{names[0]}' was empty. Supply the text you want.")
            if len(text) > limit:
                raise ToolError(f"'{names[0]}' is {len(text)} characters; keep it under {limit}.")
            return text
    raise ToolError(f"Missing required argument '{names[0]}'.")


def _as_int(arguments: dict, name: str, default: int, low: int, high: int) -> int:
    if name not in arguments or arguments[name] is None:
        return default
    value = arguments[name]
    try:
        number = int(str(value).strip())          # "3" and 3.0 both arrive in practice
    except (TypeError, ValueError):
        raise ToolError(f"'{name}' must be a whole number, not {value!r}.")
    if not low <= number <= high:
        raise ToolError(f"'{name}' must be between {low} and {high}, not {number}.")
    return number


def _coerce_arguments(raw) -> dict:
    """Tool arguments arrive as a dict, or as a JSON string, or as neither."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise ToolError("Arguments were not valid JSON.")
        if not isinstance(parsed, dict):
            raise ToolError("Arguments must be a JSON object.")
        return parsed
    if raw is None:
        return {}
    raise ToolError(f"Arguments must be a JSON object, got {type(raw).__name__}.")


def dispatch(memory, name: str, raw_arguments) -> dict:
    """Run one tool call. Always returns a dict; never raises."""
    try:
        arguments = _coerce_arguments(raw_arguments)

        if name == "search_memory":
            query = _as_text(arguments, "query", "text", "q", limit=MAX_QUERY_CHARS)
            limit = _as_int(arguments, "limit", default=3, low=1, high=MAX_RESULTS)
            hits = memory.search(query, limit=limit)
            if not hits:
                return {"ok": True, "found": 0,
                        "note": "Nothing in memory is related closely enough to that."}
            return {"ok": True, "found": len(hits), "results": hits}

        if name == "remember_fact":
            text = _as_text(arguments, "text", "fact", "content", limit=MAX_FACT_CHARS)
            fact_id = memory.remember(text)
            return {"ok": True, "fact_id": fact_id, "stored": text}

        if name == "list_facts":
            facts = memory.facts()
            return {"ok": True, "count": len(facts),
                    "facts": [{"id": fid, "text": text} for fid, text in facts]}

        if name == "forget_fact":
            key = next((k for k in ("fact_id", "id") if arguments.get(k) is not None), None)
            if key is None:
                raise ToolError("Missing required argument 'fact_id'. Call list_facts to find it.")
            fact_id = _as_int(arguments, key, default=0, low=1, high=2**31)
            if memory.forget(fact_id):
                return {"ok": True, "forgotten": fact_id}
            return {"ok": False, "error": f"No fact with id {fact_id}. Call list_facts to see what exists."}

        return {"ok": False, "error": f"No such tool '{name}'. Available: {', '.join(TOOL_NAMES)}."}

    except ToolError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:                       # never let a tool kill the turn
        return {"ok": False, "error": f"{name} failed: {exc}"}
