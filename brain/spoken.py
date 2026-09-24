"""Small text rules applied to what Alfred says aloud, kept free of the voice models so they can be tested."""

import re
import unicodedata

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


# What he calls the person in front of him, and its Portuguese. The examples teach
# "sir" and are left alone, since steering the model by instruction is what failed
# before: he keeps saying "sir", and it is swapped here, after the model and
# before the voice. Whatever title the history holds is read back as "sir" first,
# so after a switch he does not imitate the old title from the last few turns.
TITLES = {"sir": ("sir", "senhor"), "ma'am": ("ma'am", "senhora"), "madam": ("madam", "senhora")}
DEFAULT_TITLE = "sir"

# Not before a name: "Sir Isaac Newton" is a knighthood, not a way of addressing anyone.
_ANY_ENGLISH = re.compile(r"(?i:\b(?:sir|ma['’]?am|madam)\b)(?!\s+(?!I\b)[A-Z])")
_SIR = re.compile(r"(?i:\bsir\b)(?!\s+(?!I\b)[A-Z])")
# Portuguese has gender in the article too: "o senhor" is "a senhora", "ao senhor" is "à senhora".
_FEMININE = {"o": "a", "do": "da", "ao": "à", "no": "na", "pelo": "pela"}
_MASCULINE = {feminine: masculine for masculine, feminine in _FEMININE.items()}
_SENHORA = re.compile(r"(?i:\b(?:(a|da|à|na|pela)\s+)?senhora\b)")
_SENHOR = re.compile(r"(?i:\b(?:(o|do|ao|no|pelo)\s+)?senhor\b)")


def _same_case(original: str, word: str) -> str:
    return word[0].upper() + word[1:] if original[:1].isupper() else word


def _swap_portuguese(match: re.Match, articles: dict, title: str) -> str:
    article = match.group(1)
    if not article:
        return _same_case(match.group(0), title)
    return f"{_same_case(article, articles[article.lower()])} {title}"


def as_sir(text: str) -> str:
    """Any title he used, read back as "sir" / "senhor"."""
    text = _ANY_ENGLISH.sub(lambda m: _same_case(m.group(0), "sir"), text)
    return _SENHORA.sub(lambda m: _swap_portuguese(m, _MASCULINE, "senhor"), text)


def with_title(text: str, title: str) -> str:
    """ "sir" / "senhor" in `text` changed to `title` and its Portuguese."""
    if title == "sir":
        return text
    english, portuguese = TITLES[title]
    text = _SIR.sub(lambda m: _same_case(m.group(0), english), text)
    return _SENHOR.sub(lambda m: _swap_portuguese(m, _FEMININE, portuguese), text)


# "Use ma'am responses", "call me madam", "sir mode", "me chame de senhora". A
# whole-utterance command, like the language switch, so a sentence that merely
# mentions one of these words changes nothing.
_TITLE_WORDS = {"sir": "sir", "senhor": "sir", "maam": "ma'am", "mam": "ma'am", "senhora": "ma'am",
                "madam": "madam", "madame": "madam"}
_GENDER_WORDS = {"male": "sir", "man": "sir", "men": "sir", "mens": "sir",
                 "female": "ma'am", "woman": "ma'am", "women": "ma'am", "womens": "ma'am", "lady": "ma'am"}
_MODE_COMMAND = re.compile(r"^(?:please )?(?:use |switch to |go to |give me )?(?:the )?([a-z]+) "
                           r"(?:responses|replies|answers|mode)(?: please)?$")
_CALL_COMMAND = re.compile(r"^(?:please )?(?:call|address) me (?:as )?([a-z]+)(?: please| instead| from now on)*$")
# "Use ma'am", "switch back to sir": the bare title, no "responses" after it. Title
# words only - "use female" on its own is not something anyone says.
_BARE_COMMAND = re.compile(r"^(?:please )?(?:use|say|switch(?: back)? to|go(?: back)? to|change(?: back)? to|back to) "
                           r"(?:the )?([a-z]+)(?: again| instead| now| please| from now on)*$")
_CHAME_COMMAND = re.compile(r"^(?:me )?(?:chame|chama|chamar)(?: me)? de (?:o |a )?(senhora?)(?: por favor)?$")


def address_command(prompt: str) -> str | None:
    """The title this turn asks him to use (a key of TITLES), or None."""
    text = unicodedata.normalize("NFKD", prompt.lower().replace("’", "'").replace("'", ""))
    text = text.encode("ascii", "ignore").decode()
    text = " ".join(word for word in re.findall(r"[a-z]+", text) if word != "alfred")
    text = re.sub(r"\bma am\b", "maam", text)
    mode = _MODE_COMMAND.match(text)
    if mode:
        return _TITLE_WORDS.get(mode.group(1)) or _GENDER_WORDS.get(mode.group(1))
    call = _CALL_COMMAND.match(text) or _BARE_COMMAND.match(text) or _CHAME_COMMAND.match(text)
    if call:
        return _TITLE_WORDS.get(call.group(1))
    return None


def uses_title(text: str) -> bool:
    return bool(_TITLE.search(as_sir(text or "")))


class TitleRation:
    """Decides, sentence by sentence through one reply, whether the title stays, and which one it is."""

    SPACING = 2   # replies without it before it may come back

    def __init__(self, previous_replies: list[str], title: str = DEFAULT_TITLE):
        self.title = title
        self.allowed = not any(uses_title(reply) for reply in previous_replies[-self.SPACING:])

    def apply(self, sentence: str) -> str:
        sentence = as_sir(sentence)
        if not uses_title(sentence) or _ALONE.match(sentence):
            return with_title(sentence, self.title)
        if self.allowed:
            self.allowed = False
            return with_title(sentence, self.title)
        stripped = _INNER.sub(", ", sentence)
        stripped = _TRAILING.sub("", stripped)
        stripped = _LEADING.sub(lambda m: m.group(1) + m.group(2).upper(), stripped)
        return with_title(stripped, self.title)
