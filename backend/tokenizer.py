"""
tokenizer.py - splits text into tokens WITHOUT losing anything.

Joining every token's `.text` gives back the exact original string, so we can
replace single words and keep punctuation, capitalisation, spaces and line breaks.
"""
import re
from dataclasses import dataclass

# Order matters: the first alternative that matches wins.
_TOKEN_RE = re.compile(
    r"""
    (?P<url>(?:https?://|www\.)\S+)
  | (?P<email>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)
  | (?P<code>`[^`\n]*`)
  | (?P<mention>[@#]\w+)
  | (?P<alnum>\w*\d\w*)                                   # words containing digits: abc123, 3rd
  | (?P<word>[^\W\d_]+(?:['\u2019][^\W\d_]+)*)            # letters + contractions: don't, I'm
  | (?P<other>.)
    """,
    re.VERBOSE | re.DOTALL,
)

_SENTENCE_END = re.compile(r"[.!?\n]")


@dataclass
class Token:
    text: str
    start: int
    end: int
    kind: str                    # word | url | email | code | mention | alnum | other
    sentence_start: bool = False


def tokenize(text: str) -> list:
    tokens = []
    at_sentence_start = True
    for m in _TOKEN_RE.finditer(text):
        kind = m.lastgroup
        tok = Token(m.group(), m.start(), m.end(), kind)
        if kind == "word":
            tok.sentence_start = at_sentence_start
            at_sentence_start = False
        elif kind == "other" and _SENTENCE_END.search(tok.text):
            at_sentence_start = True
        tokens.append(tok)
    return tokens


def restore_case(original: str, replacement: str) -> str:
    """Give `replacement` the same capitalisation style as `original`."""
    if len(original) > 1 and original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def is_technical(word: str) -> bool:
    """ALLCAPS (API, NASA) or mixed case (FastAPI, iPhone, JavaScript): never 'correct' these."""
    if len(word) > 1 and word.isupper():
        return True
    return any(c.isupper() for c in word[1:])
