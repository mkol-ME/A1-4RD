"""Small text rules applied to what Alfred says aloud, kept free of the voice models so they can be tested."""

import re

# A sentence that is plainly Portuguese gets the Brazilian voice whatever mode the
# client is in. The client missed "Alfred switched to Portuguese", the model answered
# in Portuguese anyway, and his English voice read it out unintelligibly (2026-09-17).
# Strong markers settle it alone; weak ones need company, because English has "de"
# and "café" too.
_STRONG = re.compile(r"[ãõçê]|\b(?:não|você|senhor|senhora|obrigad[oa]|entendi|português)\b", re.I)
_WEAK = re.compile(r"(?:é|\b(?:de|da|em|isso|isto|para|com|uma|está|muito|também|então|agora|pode|vou|vai|"
                   r"que|eu|ele|ela|meu|minha|mais|bem|tudo|aqui)\b)", re.I)


def looks_portuguese(sentence: str) -> bool:
    if _STRONG.search(sentence):
        return True
    return len({match.group(0).lower() for match in _WEAK.finditer(sentence)}) >= 2


# "sir" came back in 30 of 34 replies on the first day of the new persona, and
# reads as a tic long before it reads as manners (owner, 2026-09-17). The model
# does not keep to a rate it is asked for, so the rate is kept here: at most once
# a reply, and only when neither of his last two replies had it. Once a reply and
# never twice running still came to 8 of 13. Only the vocative is removed ("Yes, sir."
# becomes "Yes."); "o senhor" meaning "you" is grammar, and a reply that is nothing
# but "Sir." is kept whole.
_TITLE = re.compile(r"\b(?:sir|senhor)\b", re.I)
_TRAILING = re.compile(r",\s*(?:sir|senhor)(?=\s*[.!?]|\s*$)", re.I)
_INNER = re.compile(r",\s*(?:sir|senhor),\s*", re.I)
_LEADING = re.compile(r"^(\W*)(?:sir|senhor),\s*(\w)", re.I)
_ALONE = re.compile(r"^\W*(?:sir|senhor)\W*$", re.I)


def uses_title(text: str) -> bool:
    return bool(_TITLE.search(text or ""))


class TitleRation:
    """Decides, sentence by sentence through one reply, whether "sir" stays."""

    SPACING = 2   # replies without it before it may come back

    def __init__(self, previous_replies: list[str]):
        self.allowed = not any(uses_title(reply) for reply in previous_replies[-self.SPACING:])

    def apply(self, sentence: str) -> str:
        if not uses_title(sentence) or _ALONE.match(sentence):
            return sentence
        if self.allowed:
            self.allowed = False
            return sentence
        stripped = _INNER.sub(", ", sentence)
        stripped = _TRAILING.sub("", stripped)
        stripped = _LEADING.sub(lambda m: m.group(1) + m.group(2).upper(), stripped)
        return stripped
