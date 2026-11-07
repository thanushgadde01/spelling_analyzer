import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from spell import SpellChecker, determine_level_and_feedback, weighted_distance, soundex   # noqa: E402
from tokenizer import tokenize, restore_case                                               # noqa: E402


@pytest.fixture(scope="module")
def checker():
    return SpellChecker()


def fix(checker, text, **kw):
    return checker.check(text, **kw).corrected


# ---- tokenizer / formatting
def test_tokenizer_is_lossless():
    text = "Hello,  world!\n\nIt's 3rd-rate; see https://a.b/c?d=1 or me@x.com `code here` #tag"
    assert "".join(t.text for t in tokenize(text)) == text


def test_punctuation_capitals_and_linebreaks_preserved(checker):
    assert fix(checker, "Hello wrold!\n\nThis,  isnt  right?") == "Hello world!\n\nThis,  isn't  right?"


def test_hello_typo_prefers_closest_word(checker):
    result = checker.check("hellu how ary you")

    assert result.corrected == "hello how are you"
    assert result.corrections[0].suggestion == "hello"
    assert result.corrections[0].applied is True


def test_case_restored():
    assert restore_case("HELLO", "world") == "WORLD"
    assert restore_case("Hello", "world") == "World"
    assert restore_case("hello", "world") == "world"


# ---- spelling
@pytest.mark.parametrize("bad,good", [
    ("the athlet ran acros the feild", "the athlete ran across the field"),
    ("she needed to seperete the papers", "she needed to separate the papers"),
    ("I havv a drream to becme a softwre enginear", "I have a dream to become a software engineer"),
])
def test_basic_typos(checker, bad, good):
    assert fix(checker, bad) == good


def test_contractions(checker):
    assert fix(checker, "I dont know, youre right, im here") == "I don't know, you're right, I'm here"
    assert fix(checker, "Don't worry, it's fine, we\u2019ve done it") == "Don't worry, it's fine, we\u2019ve done it"


def test_possessives_untouched(checker):
    t = "The teacher's book and the students' pens."
    assert fix(checker, t) == t


# ---- things that must NOT change
@pytest.mark.parametrize("text", [
    "I use FastAPI and React with JavaScript and OpenAI.",
    "Visit https://exampel.com or mail bob@exampel.com now.",
    "Run `pip instal foo` first.",
    "NASA and the API use abc123 and 3rd place.",
    "My friend Rajesh lives in Srinivas Nagar.",
    "Caf\u00e9 au lait",
])
def test_protected_text_unchanged(checker, text):
    assert fix(checker, text) == text


def test_ignore_words_and_custom_words(checker):
    assert fix(checker, "Pryia is here", ignore_words=["pryia"]) == "Pryia is here"


def test_valid_rare_words_not_changed(checker):
    t = "Serendipity and ephemeral quixotic ideas"
    assert fix(checker, t) == t


# ---- confidence
def test_low_confidence_only_suggests(checker):
    res = checker.check("teh cat", )
    c = res.corrections[0]
    assert c.original == "teh" and c.suggestions
    strict = SpellChecker(apply_threshold=0.99)
    res = strict.check("I havv a dream")
    assert res.corrected == "I havv a dream"          # nothing applied...
    assert res.spelling_mistakes == 1                   # ...but still reported
    assert res.corrections[0].applied is False and res.corrections[0].suggestion == "have"


def test_auto_correct_off(checker):
    res = checker.check("I havv a dream", auto_apply=False)
    assert res.corrected == "I havv a dream" and res.spelling_mistakes == 1


# ---- real-word / context errors
def test_context_their_there(checker):
    assert fix(checker, "I like there car and their house.") == "I like their car and their house."


def test_context_weather_whether(checker):
    assert "whether" in fix(checker, "I dont know weather it will rain")


def test_correct_confusables_left_alone(checker):
    t = "I know whether they have their car over there."
    assert fix(checker, t) == t


# ---- grammar (separate from spelling)
def test_grammar_rules(checker):
    res = checker.check("i went to a university and ate an banana. The the cat.")
    rules = {g.rule for g in res.grammar}
    assert {"LOWERCASE_I", "A_AN", "REPEATED_WORD"} <= rules
    assert res.spelling_mistakes == 0
    assert not any(g.original == "a" and g.suggestion == "an" for g in res.grammar)   # "a university" is fine


def test_subject_verb(checker):
    res = checker.check("She have a car and they is happy.")
    assert [g.suggestion for g in res.grammar if g.rule == "SUBJECT_VERB"] == ["has", "are"]


def test_grammar_offsets_point_into_original(checker):
    text = "wrold. He have it"
    g = checker.check(text).grammar[0]
    assert text[g.start:g.end] == g.original


# ---- misc
def test_empty_and_whitespace(checker):
    for t in ("", "   ", "123 456 !!!"):
        r = checker.check(t)
        assert r.total_words == 0 and r.spelling_percentage == 0 and r.corrected == t


def test_helpers():
    assert weighted_distance("teh", "the") == 1
    assert weighted_distance("cat", "cst") < weighted_distance("cat", "cpt")      # s is next to a
    assert soundex("robert") == soundex("rupert")


def test_levels():
    assert determine_level_and_feedback(0, 0)[0] == "Advanced"
    assert determine_level_and_feedback(50, 0)[0] == "Beginner"
    assert "grammar" in determine_level_and_feedback(2, 15)[1]


def test_missing_dictionary_fails_loudly():
    with pytest.raises(FileNotFoundError):
        SpellChecker(dictionary_path="/nope/missing.txt")


# ---- API
def test_api(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import server
    monkeypatch.setattr(server, "MASTER_CSV_PATH", tmp_path / "m.csv")
    with TestClient(server.app) as client:
        assert client.get("/health").json()["dictionary"]["size"] > 50000
        r = client.post("/analyze", json={"text": "I havv a drream. He have it!"}).json()
        assert r["corrected"] == "I have a dream. He have it!"
        assert r["mistakes"] == 2 and r["grammar_issues"] == 1
        assert r["corrections"][0]["original"] == "havv"
        for k in ("original", "corrected", "total_words", "mistakes", "percentage", "level", "feedback"):
            assert k in r                                  # old frontend contract intact
        s = client.post("/analyze-and-save", json={"text": "Helo wrold", "name": "T"}).json()
        assert s["success"] and (tmp_path / "m.csv").exists()
        assert client.get("/stats").json()["total_entries"] == 1
        assert client.post("/analyze", json={"text": ""}).status_code == 422
