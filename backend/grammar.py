"""
grammar.py - grammar issues, reported SEPARATELY from spelling.

1. Built-in rules (no dependencies): repeated words, a/an, lowercase "i",
   basic subject-verb agreement.
2. Optional LanguageTool (set USE_LANGUAGETOOL=1, needs Java) for the full
   grammar rule-set. Falls back silently to the built-in rules if unavailable.
"""
import logging
from dataclasses import dataclass

log = logging.getLogger("spelling.grammar")


@dataclass
class GrammarIssue:
    start: int
    end: int
    original: str
    suggestion: str
    message: str
    rule: str


# --- tables -----------------------------------------------------------------
_AN_EXCEPTIONS = {"hour", "hours", "honest", "honor", "honour", "heir"}
_A_EXCEPTIONS = ("uni", "use", "usu", "uti", "eu", "one", "once", "ubiq")
_NO_REPEAT = {"had", "that", "is", "can"}

_SV = {  # (subject, verb) -> fix
    ("he", "have"): "has", ("she", "have"): "has", ("it", "have"): "has",
    ("he", "are"): "is", ("she", "are"): "is", ("it", "are"): "is",
    ("he", "were"): "was", ("she", "were"): "was", ("it", "were"): "was",
    ("he", "do"): "does", ("she", "do"): "does", ("it", "do"): "does",
    ("he", "dont"): "doesn't", ("she", "dont"): "doesn't", ("it", "dont"): "doesn't",
    ("he", "don't"): "doesn't", ("she", "don't"): "doesn't", ("it", "don't"): "doesn't",
    ("they", "is"): "are", ("we", "is"): "are", ("you", "is"): "are",
    ("they", "was"): "were", ("we", "was"): "were", ("you", "was"): "were",
    ("they", "has"): "have", ("we", "has"): "have", ("you", "has"): "have",
    ("i", "is"): "am", ("i", "are"): "am", ("i", "has"): "have",
}


def _starts_with_vowel_sound(word: str) -> bool:
    w = word.lower()
    if w in _AN_EXCEPTIONS:
        return True
    if w.startswith(_A_EXCEPTIONS):
        return False
    return w[:1] in "aeiou"


def rule_based_issues(words):
    """words: list of (start, end, original_text, text_to_check) for word tokens, in order.
    Offsets always point into the ORIGINAL text."""
    issues = []
    for i, (s, e, orig, cur) in enumerate(words):
        low = cur.lower()
        nxt = words[i + 1] if i + 1 < len(words) else None

        # lowercase standalone "i" / "i'm" / "i've" ...
        if orig == "i" or orig.startswith("i'"):
            issues.append(GrammarIssue(s, s + 1, "i", "I", 'Write the pronoun "I" in capital letters.', "LOWERCASE_I"))

        if nxt is None:
            continue
        nlow = nxt[3].lower()

        # repeated word ("the the")
        if low == nlow and low not in _NO_REPEAT:
            issues.append(GrammarIssue(s, nxt[1], f"{orig} {nxt[2]}", orig, f'Repeated word "{low}".', "REPEATED_WORD"))

        # a / an
        if low == "a" and _starts_with_vowel_sound(nlow):
            issues.append(GrammarIssue(s, e, orig, "an" if orig.islower() else "An",
                                       f'Use "an" before "{nxt[3]}".', "A_AN"))
        elif low == "an" and not _starts_with_vowel_sound(nlow):
            issues.append(GrammarIssue(s, e, orig, "a" if orig.islower() else "A",
                                       f'Use "a" before "{nxt[3]}".', "A_AN"))

        # subject-verb agreement
        fix = _SV.get((low, nlow))
        if fix:
            issues.append(GrammarIssue(nxt[0], nxt[1], nxt[2], fix,
                                       f'Subject-verb agreement: "{cur} {nxt[3]}" -> "{cur} {fix}".', "SUBJECT_VERB"))
    return issues


# --- optional LanguageTool --------------------------------------------------
_lt = None
_lt_failed = False


def languagetool_issues(text: str):
    global _lt, _lt_failed
    if _lt_failed:
        return []
    try:
        if _lt is None:
            import language_tool_python
            _lt = language_tool_python.LanguageTool("en-US")
        out = []
        for m in _lt.check(text):
            if getattr(m, "category", "") == "TYPOS":      # spelling is handled by our engine
                continue
            out.append(GrammarIssue(
                m.offset, m.offset + m.error_length if hasattr(m, "error_length") else m.offset + m.errorLength,
                text[m.offset:m.offset + (getattr(m, "error_length", None) or m.errorLength)],
                m.replacements[0] if m.replacements else "",
                m.message, m.rule_id if hasattr(m, "rule_id") else m.ruleId))
        return out
    except Exception as exc:                                # missing package / Java / download
        log.warning("LanguageTool unavailable (%s) - using built-in grammar rules only.", exc)
        _lt_failed = True
        return []


def merge(issues_a, issues_b):
    """Combine two lists, dropping overlapping duplicates (first list wins)."""
    merged = list(issues_a)
    for b in issues_b:
        if not any(b.start < a.end and a.start < b.end for a in merged):
            merged.append(b)
    return sorted(merged, key=lambda g: g.start)
