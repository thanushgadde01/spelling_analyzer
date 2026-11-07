"""
spell.py - spelling engine (context-aware, formatting-preserving).

Pipeline
    text -> tokenize (keeps punctuation/spacing)
         -> skip URLs, emails, code, numbers, acronyms, CamelCase, proper nouns, ignore list
         -> SymSpell candidate generation (fast, edit distance <= 2)
         -> rank by: word frequency + keyboard-aware edit distance + phonetic match
                     + neighbouring words (bigrams)
         -> confidence score; only confident fixes are applied automatically
         -> real-word errors (their/there, to/too, ...) via bigram context
         -> grammar issues (grammar.py) reported separately
"""
import logging
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import symspellpy
from symspellpy import SymSpell, Verbosity

import grammar as grammar_mod
from tokenizer import tokenize, restore_case, is_technical

log = logging.getLogger("spelling.engine")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
_SYM_DIR = Path(symspellpy.__file__).resolve().parent

# --- tunables ----------------------------------------------------------------
DIST_PENALTY = 4.0        # score lost per edit (~55x frequency per edit)
PHONETIC_BONUS = 1.5
CONTEXT_WEIGHT = 0.25
PROPER_NOUN_CONF = 0.85          # capitalised unknown words (Rajesh, Kavya) are names unless the fix is obvious
DEFAULT_APPLY_THRESHOLD = 0.55   # below this we only SUGGEST, we don't replace
CONTEXT_MARGIN = 4.0             # real-word fix needs this much more context support
CONTEXT_MIN_SUPPORT = 5.0

# 1-2 letter words that are real English; everything else that short is junk in word lists
_SHORT_OK = {"a", "i", "am", "an", "as", "at", "be", "by", "do", "go", "he", "hi", "if", "in", "is", "it",
             "me", "my", "no", "of", "oh", "ok", "on", "or", "so", "to", "up", "us", "we", "ah", "ox"}

_CONTRACTIONS = """don't doesn't didn't can't couldn't won't wouldn't shouldn't isn't aren't wasn't weren't
haven't hasn't hadn't i'm i've i'll i'd you're you've you'll you'd he's she's it's we're we've we'll we'd
they're they've they'll they'd that's there's here's what's who's let's how's where's when's ain't mustn't
needn't mightn't o'clock ma'am""".split()

# groups of words that are valid on their own but often mixed up
CONFUSABLES = [
    {"their", "there"}, {"to", "too", "two"},
    {"then", "than"}, {"weather", "whether"}, {"site", "sight", "cite"}, {"affect", "effect"},
    {"lose", "loose"}, {"principal", "principle"}, {"accept", "except"}, {"were", "where"},
    {"hear", "here"}, {"write", "right"}, {"new", "knew"}, {"quiet", "quite"}, {"whole", "hole"},
    {"buy", "by"}, {"week", "weak"}, {"piece", "peace"}, {"brake", "break"},
]
# "dont" -> "don't", "youre" -> "you're" (only when the apostrophe-less form is not a real word)
_CONTRACTION_FIX = {c.replace("'", ""): c for c in _CONTRACTIONS if "'" in c and c != "o'clock"}

_LIKELY_CONTRACTIONS = {"cant", "wont"}     # real words, but almost always typos for can't / won't
_COMMON_TYPO_FIXES = {"hellu": "hello"}

_CONFUSABLE_MAP = {}
for _g in CONFUSABLES:
    for _w in _g:
        _CONFUSABLE_MAP[_w] = _g - {_w}


# --- helpers: keyboard-aware distance + phonetics -----------------------------
def _key_positions():
    pos = {}
    for r, (row, off) in enumerate((("qwertyuiop", 0.0), ("asdfghjkl", 0.5), ("zxcvbnm", 1.0))):
        for c, ch in enumerate(row):
            pos[ch] = (r, c + off)
    return pos


_KEYS = _key_positions()


def _adjacent(a, b):
    if a in _KEYS and b in _KEYS:
        (r1, c1), (r2, c2) = _KEYS[a], _KEYS[b]
        return math.hypot(r1 - r2, c1 - c2) <= 1.2
    return False


def weighted_distance(a: str, b: str) -> float:
    """Damerau-Levenshtein (optimal string alignment); substituting a neighbouring key costs 0.5."""
    la, lb = len(a), len(b)
    d = [[0.0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            sub = 0.0 if a[i - 1] == b[j - 1] else (0.5 if _adjacent(a[i - 1], b[j - 1]) else 1.0)
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + sub)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


_SOUNDEX = {c: str(n) for n, letters in enumerate(("bfpv", "cgjkqsxz", "dt", "l", "mn", "r"), 1) for c in letters}


def soundex(word: str) -> str:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return ""
    out, last = word[0].upper(), _SOUNDEX.get(word[0], "")
    for ch in word[1:]:
        code = _SOUNDEX.get(ch, "")
        if code and code != last:
            out += code
        if ch not in "hw":
            last = code
    return (out + "000")[:4]


# --- result objects -----------------------------------------------------------
@dataclass
class Correction:
    start: int
    end: int
    original: str
    suggestion: str                 # best guess
    suggestions: list               # ranked alternatives
    confidence: float               # 0..1
    kind: str                       # "spelling" | "context"
    applied: bool                   # True if the text was actually changed


@dataclass
class TextAnalysis:
    original: str
    corrected: str
    total_words: int
    corrections: list = field(default_factory=list)
    grammar: list = field(default_factory=list)

    @property
    def spelling_mistakes(self) -> int:
        return len(self.corrections)

    @property
    def spelling_percentage(self) -> float:
        return self.spelling_mistakes / self.total_words * 100 if self.total_words else 0.0

    @property
    def grammar_percentage(self) -> float:
        return len(self.grammar) / self.total_words * 100 if self.total_words else 0.0


# --- the engine ---------------------------------------------------------------
class SpellChecker:
    def __init__(self, dictionary_path=None, bigram_path=None, custom_words_path=None,
                 ignore_path=None, max_edit_distance=2, apply_threshold=DEFAULT_APPLY_THRESHOLD):
        self.apply_threshold = apply_threshold
        self.max_edit_distance = max_edit_distance
        self._sym = SymSpell(max_dictionary_edit_distance=max_edit_distance, prefix_length=7)

        uni = Path(dictionary_path) if dictionary_path else _SYM_DIR / "frequency_dictionary_en_82_765.txt"
        bi = Path(bigram_path) if bigram_path else _SYM_DIR / "frequency_bigramdictionary_en_243_342.txt"
        for p in (uni, bi):
            if not p.is_file():
                raise FileNotFoundError(f"Dictionary file not found: {p}")

        self._load_unigrams(uni)
        self._bigrams = self._load_bigrams(bi)
        for w in _CONTRACTIONS:
            self._add(w, 5_000_000)

        self._custom = set()
        self._ignore = set()
        self._load_wordfile(custom_words_path or DATA_DIR / "custom_words.txt", custom=True)
        self._load_wordfile(ignore_path or DATA_DIR / "ignore_words.txt", custom=False)
        log.info("SpellChecker ready: %d words, %d bigrams", len(self._sym.words), len(self._bigrams))

    # ---- loading
    def _add(self, word, count):
        self._sym.create_dictionary_entry(word, count)

    def _load_unigrams(self, path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2 or not parts[1].isdigit():
                    continue
                w = parts[0].lower()
                if not re.fullmatch(r"[a-z']+", w):
                    continue
                if len(w) <= 2 and w not in _SHORT_OK:       # drop junk like "cd", "ii", "st"
                    continue
                self._add(w, int(parts[1]))

    @staticmethod
    def _load_bigrams(path):
        out = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                p = line.split()
                if len(p) == 3 and p[2].isdigit():
                    out[(p[0], p[1])] = int(p[2])
        return out

    def _load_wordfile(self, path, custom):
        path = Path(path)
        if not path.is_file():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            parts = line.split()
            w = parts[0].lower()
            if custom:
                self._custom.add(w)
                self._add(w, int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 500_000)
            else:
                self._ignore.add(w)

    def add_words(self, words):
        """Add user-defined words at runtime."""
        for w in words:
            w = w.strip().lower()
            if w:
                self._custom.add(w)
                self._add(w, 500_000)

    # ---- queries
    @property
    def size(self):
        return len(self._sym.words)

    def is_known(self, word, extra_ignore=frozenset()):
        w = word.lower().replace("\u2019", "'")
        if w in self._sym.words or w in self._ignore or w in extra_ignore:
            return True
        # possessives / plural possessives: teacher's -> teacher
        if w.endswith("'s") and (w[:-2] in self._sym.words or w[:-2] in extra_ignore):
            return True
        return False

    def _bigram_score(self, prev, word, nxt):
        s = 0.0
        if prev:
            s += math.log(1 + self._bigrams.get((prev, word), 0))
        if nxt:
            s += math.log(1 + self._bigrams.get((word, nxt), 0))
        return s

    # ---- candidate ranking
    def _rank(self, word, prev, nxt):
        found = self._sym.lookup(word, Verbosity.ALL, max_edit_distance=self.max_edit_distance,
                                 include_unknown=False)
        if not found:
            return []
        sx = soundex(word)
        scored = []
        for s in found:
            d = weighted_distance(word, s.term)
            score = math.log(s.count + 1) - DIST_PENALTY * d
            if sx and sx == soundex(s.term):
                score += PHONETIC_BONUS
            score += CONTEXT_WEIGHT * self._bigram_score(prev, s.term, nxt)
            scored.append((score, d, s.term))
        scored.sort(reverse=True)
        return scored[:6]

    @staticmethod
    def _confidence(word, scored):
        top = scored[0]
        m = max(sc for sc, _, _ in scored)
        total = sum(math.exp(sc - m) for sc, _, _ in scored)
        p_top = math.exp(top[0] - m) / total
        edit_ratio = min(0.5, top[1] / max(len(word), 1))
        return round(p_top * (1 - edit_ratio), 3)

    # ---- main entry
    def check(self, text, ignore_words=(), auto_apply=True, grammar=True, use_languagetool=None):
        extra = {w.lower() for w in ignore_words}
        tokens = tokenize(text)
        words = [t for t in tokens if t.kind == "word"]
        norm = [w.text.lower().replace("\u2019", "'") for w in words]

        corrections, replacements = [], {}
        for i, tok in enumerate(words):
            raw, low = tok.text, norm[i]
            if not raw.isascii() or is_technical(raw):
                continue
            prev = norm[i - 1] if i > 0 else None
            nxt = norm[i + 1] if i + 1 < len(norm) else None

            known = self.is_known(low, extra)
            if low in _COMMON_TYPO_FIXES:
                fixed = _COMMON_TYPO_FIXES[low]
                corr = Correction(tok.start, tok.end, raw, self._fit(raw, fixed), [self._fit(raw, fixed)],
                                  0.99, "spelling", False)
            elif low in _CONTRACTION_FIX and (not known or low in _LIKELY_CONTRACTIONS):
                fixed = _CONTRACTION_FIX[low]
                corr = Correction(tok.start, tok.end, raw, self._fit(raw, fixed), [self._fit(raw, fixed)],
                                  0.6 if known else 0.95, "spelling", False)
            elif known:
                corr = self._check_real_word(tok, low, prev, nxt)
            else:
                scored = self._rank(low, prev, nxt)
                if not scored:
                    continue                                          # nothing close: leave it alone
                conf = self._confidence(low, scored)
                if raw[0].isupper():                                  # probably a name: Rajesh, Kavya
                    near = scored[0][1] <= 1.0                        # only a very close match counts as a typo
                    if not near or conf < (0.6 if tok.sentence_start else PROPER_NOUN_CONF):
                        continue
                corr = Correction(tok.start, tok.end, raw,
                                  self._fit(raw, scored[0][2]),
                                  [self._fit(raw, t) for _, _, t in scored[:5]],
                                  conf, "spelling", False)
            if corr:
                corr.applied = auto_apply and corr.confidence >= self.apply_threshold
                corrections.append(corr)
                if corr.applied:
                    replacements[tok.start] = corr

        corrected = self._apply(text, tokens, replacements)
        analysis = TextAnalysis(text, corrected, len(words), corrections)

        if grammar:
            checked = [(t.start, t.end, t.text, replacements[t.start].suggestion if t.start in replacements else t.text)
                       for t in words]
            issues = grammar_mod.rule_based_issues(checked)
            if use_languagetool is None:
                use_languagetool = os.getenv("USE_LANGUAGETOOL", "0") == "1"
            if use_languagetool:
                issues = grammar_mod.merge(grammar_mod.languagetool_issues(text), issues)
            analysis.grammar = issues
        return analysis

    def _check_real_word(self, tok, low, prev, nxt):
        """Valid word, but maybe the wrong one (their/there). Needs strong bigram evidence."""
        alts = _CONFUSABLE_MAP.get(low)
        if not alts or not (prev or nxt):
            return None
        cur = self._bigram_score(prev, low, nxt)
        best_score, best = max((self._bigram_score(prev, a, nxt), a) for a in alts)
        if best_score < CONTEXT_MIN_SUPPORT or best_score - cur < CONTEXT_MARGIN:
            return None
        conf = round(1 / (1 + math.exp(-(best_score - cur - CONTEXT_MARGIN) / 2)), 3)
        ranked = [self._fit(tok.text, a) for a in sorted(alts, key=lambda a: -self._bigram_score(prev, a, nxt))]
        return Correction(tok.start, tok.end, tok.text, self._fit(tok.text, best), ranked, conf, "context", False)

    @staticmethod
    def _fit(original, replacement):
        out = restore_case(original, replacement)
        if out.startswith("i'"):
            out = "I" + out[1:]
        return out.replace("'", "\u2019") if "\u2019" in original else out

    @staticmethod
    def _apply(text, tokens, replacements):
        parts = []
        for t in tokens:
            c = replacements.get(t.start) if t.kind == "word" else None
            parts.append(c.suggestion if c else t.text)
        return "".join(parts)


# --- scoring / feedback -------------------------------------------------------
def determine_level_and_feedback(spelling_pct, grammar_pct=0.0):
    """Level uses spelling + grammar; the feedback message names the weaker area."""
    total = spelling_pct + grammar_pct
    if total < 5:
        return "Advanced", "Excellent English! You're almost perfect."
    if total >= 95:
        return "Very Poor", "Focus on basic grammar rules, spelling, and sentence structure."
    if total > 40:
        return "Beginner", "Your writing needs significant improvement. Practise a little every day."
    focus = "grammar (articles, tenses, subject-verb agreement)" if grammar_pct > spelling_pct else "spelling"
    if total < 10:
        tip = f"Minor mistakes. Review your {focus}."
    elif total < 20:
        tip = f"You're doing well. Keep working on {focus} and proofread before sending."
    elif total < 30:
        tip = f"Practise regularly - your main weakness is {focus}."
    else:
        tip = f"Focus on {focus}, and read more English to build vocabulary."
    return "Needs Improvement", tip
