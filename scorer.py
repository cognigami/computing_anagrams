"""
scorer.py — ranks anagram candidates by profile.

pip install wordfreq nltk
python -c "import nltk; nltk.download('brown')"

Usage:
    python scorer.py results.csv --profile institutional --top 50
    python scorer.py results.csv --profile law_firm --top 50
    python scorer.py results.csv --profile medical --top 50 --require-w3
    python scorer.py results.csv --profile institutional --min-words 2 --max-words 3
"""

import argparse
import csv
import math
import sys
from collections import Counter
from itertools import permutations

from profiles import PROFILES, PROFILE_NAMES

# ---------------------------------------------------------------------------
# Optional dependencies — degrade gracefully if missing
# ---------------------------------------------------------------------------
try:
    from wordfreq import word_frequency
    HAS_WORDFREQ = True
except ImportError:
    print("Warning: wordfreq not found. Frequency scoring disabled.", file=sys.stderr)
    HAS_WORDFREQ = False

try:
    from nltk import bigrams
    from nltk.corpus import brown
    HAS_NLTK = True
except ImportError:
    print("Warning: nltk not found. Bigram fluency scoring disabled.", file=sys.stderr)
    HAS_NLTK = False

# ---------------------------------------------------------------------------
# Bigram model (built once from Brown corpus)
# ---------------------------------------------------------------------------
_bigram_model = None

def build_bigram_model():
    global _bigram_model
    if _bigram_model is not None:
        return
    try:
        words = [w.lower() for w in brown.words()]
        bi = list(bigrams(words))
        counts = Counter(bi)
        unigram_counts = Counter(words)
        _bigram_model = (counts, unigram_counts)
        print("Bigram model ready.", file=sys.stderr)
    except Exception as e:
        print(f"Warning: could not build bigram model: {e}", file=sys.stderr)
        _bigram_model = None

def bigram_log_prob(phrase_words):
    """Average log bigram probability for a phrase. Higher = more fluent."""
    if not HAS_NLTK or _bigram_model is None:
        return 0.0
    counts, unigram_counts = _bigram_model
    tokens = ["<s>"] + phrase_words + ["</s>"]
    log_prob = 0.0
    n = 0
    for w1, w2 in bigrams(tokens):
        c_bi = counts.get((w1, w2), 0)
        c_uni = unigram_counts.get(w1, 0)
        p = (c_bi + 1) / (c_uni + len(unigram_counts) + 1)
        log_prob += math.log(p)
        n += 1
    return log_prob / max(n, 1)

# ---------------------------------------------------------------------------
# Frequency scoring
# ---------------------------------------------------------------------------
def avg_word_frequency(words):
    """Log-average wordfreq frequency. Higher = more common = more boring = good."""
    if not HAS_WORDFREQ:
        return 0.0
    freqs = [word_frequency(w, "en") for w in words]
    log_freqs = [math.log(f + 1e-9) for f in freqs]
    return sum(log_freqs) / len(log_freqs)

# ---------------------------------------------------------------------------
# Pattern matching engine
# ---------------------------------------------------------------------------
def pattern_multiplier(words, profile):
    """
    Check whether any permutation of `words` satisfies any pattern in the
    profile. Returns a multiplier:
        1.0                          — no match
        1 + pattern_partial_bonus    — partial match (all but one slot)
        1 + pattern_bonus            — full match

    A pattern is a tuple of category names, e.g. ("surname", "legal").
    A word matches a category slot if it appears in profile["categories"][slot].
    Patterns shorter than the word list are checked against any contiguous
    subsequence; patterns longer than the word list are skipped.
    """
    patterns  = profile.get("patterns")
    cats      = profile.get("categories")
    if not patterns or not cats:
        return 1.0

    full_bonus    = profile.get("pattern_bonus",         0.5)
    partial_bonus = profile.get("pattern_partial_bonus", 0.2)

    best = 0.0  # 0 = no match, 1 = partial, 2 = full

    for perm in permutations(words):
        for pattern in patterns:
            plen = len(pattern)
            wlen = len(perm)

            if plen > wlen:
                continue  # can't satisfy a longer pattern with fewer words

            # Try the pattern against every contiguous window of `plen` words
            for start in range(wlen - plen + 1):
                window = perm[start:start + plen]
                matches = sum(
                    1 for word, cat in zip(window, pattern)
                    if word in cats.get(cat, set())
                )
                if matches == plen:
                    best = 2.0
                    break  # full match — nothing better possible
                elif matches == plen - 1:
                    best = max(best, 1.0)

            if best == 2.0:
                break
        if best == 2.0:
            break

    if best == 2.0:
        return 1.0 + full_bonus
    elif best == 1.0:
        return 1.0 + partial_bonus
    else:
        return 1.0

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
DEFAULT_WORD_COUNT_SCORES = {1: 10, 2: 80, 3: 100, 4: 70, 5: 40}

def score_candidate(words, profile):
    """
    Score a list of words against a profile.
    Base score is 0–100; pattern multiplier can push it higher.
    """
    n = len(words)
    weights  = profile["weights"]
    vocab    = profile["vocab"]
    surnames = profile.get("surnames")
    wc_scores = profile.get("word_count_scores", DEFAULT_WORD_COUNT_SCORES)

    # 1. Word count
    wc_score = wc_scores.get(n, 20)

    # 2. Vocab / surname bonus
    if surnames is not None:
        # Surname-density score replaces plain vocab hit-rate
        surname_hits = sum(1 for w in words if w in surnames)
        vocab_score = (surname_hits / max(n, 1)) * 100
    else:
        vocab_hits = sum(1 for w in words if w in vocab)
        vocab_score = min(vocab_hits / max(n, 1), 1.0) * 100

    # 3. Word frequency (boring = good; normalise -20..–5 → 0..100)
    freq_score = avg_word_frequency(words)
    freq_normalised = max(0.0, min(100.0, (freq_score + 20) * (100 / 15)))

    # 4. Bigram fluency — best permutation wins (cap at 4! = 24)
    if HAS_NLTK and _bigram_model:
        perms = list(permutations(words))[:24]
        best_fluency = max(bigram_log_prob(list(p)) for p in perms)
        fluency_normalised = max(0.0, min(100.0, (best_fluency + 8) * (100 / 5)))
    else:
        fluency_normalised = 0.0

    # Weighted base score
    raw = (
        wc_score           * weights["word_count"] +
        vocab_score        * weights["vocab"]      +
        freq_normalised    * weights["frequency"]  +
        fluency_normalised * weights["fluency"]
    )

    # Rescale if fluency was unavailable
    if not (HAS_NLTK and _bigram_model):
        used_weight = 1.0 - weights["fluency"]
        raw = raw / used_weight if used_weight > 0 else raw

    # 5. Pattern multiplier (multiplicative — can push score above 100)
    multiplier = pattern_multiplier(words, profile)
    final = raw * multiplier

    return round(final, 2), round(multiplier, 2)

# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------
def load_csv(path):
    """
    Expects: word1, word2, leftover_letters, [word3]
    Returns list of (words, leftovers_str, raw_row)
    """
    rows = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            w1 = row[0].strip().lower()
            w2 = row[1].strip().lower()
            leftovers = row[2].strip() if len(row) > 2 else ""
            w3 = row[3].strip().lower() if len(row) > 3 and row[3].strip() else None
            words = [w for w in [w1, w2, w3] if w]
            rows.append((words, leftovers, row))
    return rows

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Score and rank anagram candidates by profile.")
    parser.add_argument("csv", help="Input CSV from generator")
    parser.add_argument(
        "--profile", default="institutional",
        choices=PROFILE_NAMES,
        help=f"Scoring profile to use. Available: {', '.join(PROFILE_NAMES)}"
    )
    parser.add_argument("--top",       type=int, default=50)
    parser.add_argument("--min-words", type=int, default=2)
    parser.add_argument("--max-words", type=int, default=4)
    parser.add_argument(
        "--require-w3", action="store_true",
        help="Only score rows where leftovers resolved to a third word"
    )
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    print(f"\nProfile : {args.profile}", file=sys.stderr)
    print(f"         {profile['description']}", file=sys.stderr)

    if HAS_NLTK:
        build_bigram_model()

    print(f"Loading {args.csv}...", file=sys.stderr)
    rows = load_csv(args.csv)
    print(f"Loaded {len(rows)} rows.", file=sys.stderr)

    scored = []
    for words, leftovers, raw in rows:
        if not (args.min_words <= len(words) <= args.max_words):
            continue
        if args.require_w3 and len(words) < 3:
            continue

        final, multiplier = score_candidate(words, profile)
        phrase = " ".join(w.capitalize() for w in words)
        leftover_note = f"  [{leftovers}]" if leftovers else ""
        # Show multiplier only when pattern matching is active and fired
        mult_note = f"  ×{multiplier}" if multiplier > 1.0 else ""
        scored.append((final, phrase, leftover_note, mult_note))

    scored.sort(key=lambda x: x[0], reverse=True)

    print(f"\n{'Rank':<6} {'Score':<8} Phrase")
    print("-" * 60)
    for i, (s, phrase, note, mult) in enumerate(scored[:args.top], 1):
        print(f"{i:<6} {s:<8} {phrase}{note}{mult}")

    print(f"\n(Showing top {min(args.top, len(scored))} of {len(scored)} scored rows)")

if __name__ == "__main__":
    main()
