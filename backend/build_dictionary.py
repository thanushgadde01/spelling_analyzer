"""
build_dictionary.py - build a clean word-frequency file from several sources.

    python build_dictionary.py --out data/frequency_dictionary.txt \
        --freq-file path/to/other_freq.txt --corpus big.txt --corpus-weight 0.1

Sources
  base        bundled SymSpell list (clean, 82k words)                 [default]
  --freq-file extra "word count" lists
  --corpus    raw text (books, articles). Cleaned before counting:
              Project Gutenberg header/footer removed, words that are mostly
              capitalised mid-sentence (names) dropped, rare words dropped.
Then set  DICT_PATH=data/frequency_dictionary.txt  to use it.
"""
import argparse
import re
from collections import Counter
from pathlib import Path

import symspellpy

BASE = Path(symspellpy.__file__).parent / "frequency_dictionary_en_82_765.txt"
WORD = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")


def clean_corpus_counts(text, min_count=5, max_name_ratio=0.5):
    # cut header/footer (works for both old and new Gutenberg markers)
    m = re.search(r"\*\*\* ?START OF .*?\*\*\*", text, re.I | re.S)
    if m:
        text = text[m.end():]
    m = re.search(r"\*\*\* ?END OF ", text, re.I)
    if m:
        text = text[:m.start()]
    text = re.sub(r"(?im)^.*(copyright|project gutenberg|ebook|chapter [ivxlc\d]+).*$", " ", text)

    lower, cap_mid = Counter(), Counter()
    for m in WORD.finditer(text):
        w = m.group()
        lower[w.lower()] += 1
        before = text[max(0, m.start() - 2):m.start()]
        if w[0].isupper() and not re.search(r"[.!?\"\u201c]\s*$|^\s*$|\n\s*$", before) and m.start() > 2:
            cap_mid[w.lower()] += 1
    return Counter({w: c for w, c in lower.items()
                    if c >= min_count and cap_mid[w] / c <= max_name_ratio and len(w) > 2})


def read_freq(path):
    out = Counter()
    for line in open(path, encoding="utf-8"):
        p = line.split()
        if len(p) == 2 and p[1].isdigit():
            out[p[0].lower()] += int(p[1])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/frequency_dictionary.txt")
    ap.add_argument("--freq-file", action="append", default=[])
    ap.add_argument("--corpus", action="append", default=[])
    ap.add_argument("--corpus-weight", type=float, default=0.1, help="corpus counts are scaled by this")
    ap.add_argument("--min-count", type=int, default=5)
    a = ap.parse_args()

    merged = read_freq(BASE)
    for f in a.freq_file:
        merged.update(read_freq(f))
    for c in a.corpus:
        text = Path(c).read_text(encoding="utf-8", errors="ignore")
        counts = clean_corpus_counts(text, a.min_count)
        # scale corpus counts into the same range as the base list
        scale = max(merged.values()) / max(counts.values()) * a.corpus_weight if counts else 0
        for w, n in counts.items():
            merged[w] += int(n * scale / 1000) + 1
        print(f"{c}: kept {len(counts):,} clean words")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for w, n in merged.most_common():
            f.write(f"{w} {n}\n")
    print(f"Wrote {len(merged):,} words -> {a.out}")


if __name__ == "__main__":
    main()
