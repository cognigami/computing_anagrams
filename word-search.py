from collections import Counter
from itertools import combinations

# ----------------------------
# Configuration
# ----------------------------
PHRASE = "" # TODO: Make this a command-line option
POOL = Counter(PHRASE)
VOWELS = set("aeiou")
ENABLE_PATH = "enable1.txt"          # adjust if needed
MACOS_PATH = "/usr/share/dict/words"
MIN_WORD_LEN = 4
MAX_WORD_LEN = 10
MAX_LEFTOVER = 4    # how many letters you're willing to tolerate unused

# ----------------------------
# Helpers
# ----------------------------
def load_words(path):
    with open(path) as f:
        return {
            w.strip().lower()
            for w in f
            if w.strip().isalpha()
        }

def has_vowel(word):
    return any(c in VOWELS for c in word)

def can_form(word, pool):
    """True if word can be formed from pool"""
    return not (Counter(word) - pool)

def subtract(pool, word):
    """Return remaining letters after removing word"""
    return pool - Counter(word)

# ----------------------------
# Load dictionaries
# ----------------------------
enable = load_words(ENABLE_PATH)
macos = load_words(MACOS_PATH)

# union for discovery; macos used later as a sanity check
WORDS = enable | macos

# Pre-build a lookup: frozenset-of-letters -> list of words
# Used for fast leftover matching
from collections import defaultdict
letters_to_words = defaultdict(list)
for w in WORDS:
    if MIN_WORD_LEN <= len(w) <= MAX_WORD_LEN and has_vowel(w):
        letters_to_words[frozenset(Counter(w).items())].append(w)

# ----------------------------
# Step 1: pre-filter candidate words
# ----------------------------
candidates = [
    w for w in WORDS
    if MIN_WORD_LEN <= len(w) <= MAX_WORD_LEN
    and has_vowel(w)
    and can_form(w, POOL)
]
print(f"{len(candidates)} candidate words")

# ----------------------------
# Step 2: two-word subtraction search
# ----------------------------
results = []
for w1, w2 in combinations(candidates, 2):
    rem1 = subtract(POOL, w1)
    if not can_form(w2, rem1):
        continue
    rem2 = subtract(rem1, w2)
    leftover_len = sum(rem2.values())
    if leftover_len > MAX_LEFTOVER:
        continue

    # optional readability filter:
    # at least one "normal" dictionary word
    if not (w1 in macos or w2 in macos):
        continue

    # Attempt to match leftovers to a third word ---
    w3 = None
    if leftover_len >= MIN_WORD_LEN:
        key = frozenset(rem2.items())
        matches = letters_to_words.get(key, [])
        if matches:
            # Prefer macos words; otherwise take the first match
            w3 = next((m for m in matches if m in macos), matches[0])

    results.append((w1, w2, rem2, w3))

# ----------------------------
# Step 3: display results
# ----------------------------
for w1, w2, rem, w3 in results:
    leftover = " ".join(sorted(rem.elements()))
    w3_str = w3 if w3 else ""
    print(f"{w1},{w2},{leftover},{w3_str}")

print(f"\nTotal results: {len(results)}")

if __name__ == "__main__":
    pass
