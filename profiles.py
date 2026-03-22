"""
profiles.py — scoring profiles for the anagram scorer.

Each profile has:
  - description: human-readable summary
  - vocab: set of words that earn a base bonus for this profile
  - weights: dict of scoring component weights (must sum to 1.0)
      keys: word_count, vocab, frequency, fluency
  - word_count_scores: override the default word-count reward curve
      (optional; falls back to scorer default if omitted)

  OPTIONAL — pattern matching (multiplicative score boost):
  - categories: dict mapping category name -> set of words
  - patterns: list of tuples of category names, e.g.
        [("surname", "surname"), ("surname", "legal")]
      The scorer tries all permutations of the phrase words and checks
      whether any permutation satisfies any pattern (left to right).
      A full match multiplies the score by (1 + pattern_bonus).
      A partial match (all but one slot filled) multiplies by a smaller bonus.
  - pattern_bonus: multiplier added on full match, e.g. 0.5 → score *= 1.5
  - pattern_partial_bonus: multiplier for a partial match, e.g. 0.2 → score *= 1.2

  OPTIONAL — surname scoring (replaces vocab bonus when present):
  - surnames: set of words considered plausible surnames from the letter pool.
      When present, the vocab score is replaced by a surname-density score:
      (matched surnames / total words) * 100. This is then weighted by
      weights["vocab"] as usual.

Add as many profiles as you like. Pass --profile <key> to scorer.py.
"""

# ---------------------------------------------------------------------------
# Shared word sets (referenced across multiple profiles)
# ---------------------------------------------------------------------------

# Surnames plausibly formable from SECRETDECODERRING
# Focus: words that could appear on a brass plaque without raising eyebrows
_SDR_SURNAMES = {
    "corder", "deering", "greening", "norris", "gordon", "reeding",
    "grinder", "cordiner", "corrigan", "cronin", "decor", "reding",
    "decker", "reed", "noel", "corned", "grendel", "nicod",
    "creede", "gerend", "roden", "creed",
}

_LEGAL_WORDS = {
    "partners", "associates", "solicitors", "barristers", "counsel",
    "legal", "law", "group", "firm", "office", "offices",
    "incorporated", "registered", "international", "general",
}

_FACILITY_WORDS = {
    "clinic", "clinics", "center", "centre", "centers", "centres",
    "hospital", "institute", "institutes", "medical",
    "research", "health", "network", "regional", "national", "general",
}

_MEDICAL_DESCRIPTORS = {
    "genetic", "genetics", "surgical", "diagnostic", "centric",
    "ergodic", "necrosed", "crinoid", "nordic", "scenic",
    "recoding", "decoding", "oncologic",
}

_GEO_WORDS = {
    "ridge", "crest", "grove", "crossing",
    "northern", "eastern", "western", "southern",
    "north", "south", "east", "west",
}

# ---------------------------------------------------------------------------

PROFILES = {

    # -------------------------------------------------------------------------
    "institutional": {
        "description": "Government agencies, councils, bureaus, civic bodies.",
        "vocab": {
            # org types
            "institute", "institution", "center", "centre", "council", "office",
            "bureau", "agency", "department", "division", "commission", "committee",
            "foundation", "society", "association", "corporation", "incorporated",
            "services", "solutions", "consulting", "group", "network", "systems",
            "industries", "enterprises", "partners", "associates", "international",
            "national", "federal", "regional", "general", "central", "united",
            # geography
            *_GEO_WORDS,
            # workaday fillers
            "science", "sciences", "research", "records", "resource", "resources",
            "data", "information", "security", "intelligence", "engineering",
            "technology", "technologies", "design", "strategic", "operations",
            # plausible surnames
            *_SDR_SURNAMES,
        },
        "weights": {
            "word_count": 0.20,
            "vocab":      0.30,
            "frequency":  0.25,
            "fluency":    0.25,
        },
        "word_count_scores": {1: 10, 2: 75, 3: 100, 4: 60, 5: 30},
        # No pattern matching — institutional names are too varied in structure
    },

    # -------------------------------------------------------------------------
    "law_firm": {
        "description": "Solicitors, barristers, partners — the kind of brass plaque name.",

        # vocab is used only for the base weighted score here;
        # the real work is done by surnames + patterns
        "vocab": _LEGAL_WORDS,

        # Surname scoring replaces the vocab bonus when present
        "surnames": _SDR_SURNAMES,

        "weights": {
            "word_count": 0.15,
            "vocab":      0.30,   # drives surname-density score
            "frequency":  0.20,
            "fluency":    0.35,
        },
        "word_count_scores": {1: 10, 2: 100, 3: 85, 4: 55, 5: 15},

        # Pattern matching — multiplicative boost
        "categories": {
            "surname": _SDR_SURNAMES,
            "legal":   _LEGAL_WORDS,
        },
        "patterns": [
            ("surname", "surname"),           # Corder Greening
            ("surname", "surname", "legal"),  # Corder Greening Associates
            ("surname", "legal"),             # Greening Solicitors
            ("legal",   "surname"),           # Associates: less common but valid
        ],
        "pattern_bonus":         0.60,   # full match  → score *= 1.60
        "pattern_partial_bonus": 0.25,   # partial match → score *= 1.25
    },

    # -------------------------------------------------------------------------
    "medical": {
        "description": "Hospitals, clinics, medical centres, research institutes.",
        "vocab": {
            *_FACILITY_WORDS,
            *_MEDICAL_DESCRIPTORS,
            # geography (hospitals love a good ridge or crest — but de-weighted
            # vs institutional by keeping this list smaller)
            "ridge", "crest", "northern", "eastern", "western", "southern",
            # donor / founder surnames
            *_SDR_SURNAMES,
        },
        "weights": {
            "word_count": 0.15,
            "vocab":      0.30,
            "frequency":  0.15,
            "fluency":    0.40,   # bumped: medical names need to *sound* credible
        },
        "word_count_scores": {1: 10, 2: 70, 3: 100, 4: 90, 5: 40},

        # Pattern matching — multiplicative boost
        "categories": {
            "surname":    _SDR_SURNAMES,
            "descriptor": _MEDICAL_DESCRIPTORS,
            "facility":   _FACILITY_WORDS,
            "geo":        _GEO_WORDS,
        },
        "patterns": [
            ("descriptor", "facility"),            # Genetic Centre
            ("surname",    "facility"),            # Corder Institute
            ("geo",        "facility"),            # Ridge Clinic
            ("descriptor", "geo", "facility"),     # Genetic Ridge Centre
            ("surname",    "descriptor", "facility"), # Corder Genetic Institute
            ("geo",        "descriptor", "facility"),  # Ridge Genetic Centre
        ],
        "pattern_bonus":         0.55,
        "pattern_partial_bonus": 0.20,
    },

}

# Convenience: list available profile names
PROFILE_NAMES = list(PROFILES.keys())
