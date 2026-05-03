"""Composite brandability scorer.

Combines multiple cheap, local scorers into a single 0-1 brandability score
suitable for ranking large candidate sets before expensive network checks.
"""

from brand.registry import scorers


# ---------------------------------------------------------------------------
# Sub-score helpers (inlined to avoid circular imports with other scorer modules)
# ---------------------------------------------------------------------------


def _syllable_count(name: str) -> int:
    """Count syllables via vowel-group heuristic."""
    import re

    groups = re.findall(r"[aeiouy]+", name.lower())
    count = len(groups)
    if name.lower().endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _vowel_consonant_ratio(name: str) -> float:
    """Ratio of vowels to total letters (ideal ~0.4-0.5 for pronounceability)."""
    vowels = sum(1 for c in name.lower() if c in "aeiouy")
    return vowels / len(name) if name else 0.0


def _unique_letter_ratio(name: str) -> float:
    """Ratio of unique letters to total (higher = more varied)."""
    return len(set(name.lower())) / len(name) if name else 0.0


def _has_repeating_pattern(name: str) -> bool:
    """Check for simple repetition like 'bababa', 'ababab'."""
    n = name.lower()
    half = len(n) // 2
    if half >= 2 and n[:half] == n[half : 2 * half]:
        return True
    # Check 2-char repeating unit
    if len(n) >= 4:
        unit = n[:2]
        if unit * (len(n) // 2) == n[: len(unit) * (len(n) // 2)]:
            return True
    return False


_FRONT_VOWELS = set("eiy")
_BACK_VOWELS = set("oua")
_VOICELESS = set("ptksfc")
_VOICED = set("bdgvzjmnlr")

# Substrings that evoke positive associations for tech/health/science
_POSITIVE_MORPHEMES = {
    "lum",
    "clar",
    "viv",
    "sol",
    "zen",
    "neo",
    "nov",
    "lux",
    "vita",
    "sana",
    "medi",
    "cura",
    "vis",
    "gen",
    "syn",
    "evo",
    "acu",
    "cog",
    "sen",
    "ana",
    "lex",
    "dyn",
    "val",
    "ven",
    "ori",
    "ver",
    "era",
    "alo",
    "elu",
    "avi",
    "iri",
    "umi",
    "elu",
}

# Common profanity substrings (minimal list)
_BAD_SUBSTRINGS = {
    "ass",
    "damn",
    "shit",
    "fuck",
    "dick",
    "cock",
    "cunt",
    "piss",
    "slut",
    "nazi",
    "rape",
    "porn",
    "anal",
    "anus",
    "tit",
    "nig",
    "fag",
    "cum",
    "poo",
}

# Ambiguous graphemes (from linguistic.py)
_AMBIGUOUS_GRAPHEMES = {
    "c": 2,
    "g": 2,
    "th": 2,
    "ough": 6,
    "ch": 3,
    "gh": 2,
    "ea": 3,
    "oo": 2,
    "ou": 3,
    "x": 2,
}


def _spelling_transparency(name: str) -> float:
    """Score 0-1 for how unambiguously the name maps to one pronunciation."""
    name_lower = name.lower()
    ambiguity = 0
    for grapheme, n_pron in _AMBIGUOUS_GRAPHEMES.items():
        count = name_lower.count(grapheme)
        if count > 0:
            ambiguity += count * (n_pron - 1)
    max_ambiguity = len(name_lower) * 2
    if max_ambiguity == 0:
        return 1.0
    return max(0.0, 1.0 - ambiguity / max_ambiguity)


def _novelty(name: str) -> float:
    """1.0 = completely novel, 0.0 = very common word."""
    try:
        from wordfreq import zipf_frequency

        freq = zipf_frequency(name.lower(), "en")
        if freq == 0:
            return 1.0
        return max(0.0, 1.0 - freq / 7.0)
    except ImportError:
        return 0.5  # unknown, neutral


def _has_hazard(name: str) -> bool:
    """Quick check for profanity substrings."""
    name_lower = name.lower()
    for window in range(3, 7):
        for i in range(len(name_lower) - window + 1):
            if name_lower[i : i + window] in _BAD_SUBSTRINGS:
                return True
    return False


def _positive_morpheme_score(name: str) -> float:
    """0-1 score for presence of positive morpheme substrings."""
    name_lower = name.lower()
    matches = sum(1 for m in _POSITIVE_MORPHEMES if m in name_lower)
    # Cap at 3 matches = 1.0
    return min(1.0, matches / 3.0)


# ---------------------------------------------------------------------------
# Consonant cluster penalty
# ---------------------------------------------------------------------------

_HARSH_CLUSTERS = {
    "bk",
    "bz",
    "dk",
    "dz",
    "fk",
    "gk",
    "gz",
    "hk",
    "kg",
    "kz",
    "mk",
    "pk",
    "pz",
    "tk",
    "tz",
    "vk",
    "vz",
    "zb",
    "zd",
    "zf",
    "zg",
    "zk",
    "zm",
    "zn",
    "zp",
    "zt",
    "zv",
    "bf",
    "fb",
    "gf",
    "fg",
    "pf",
    "kf",
    "fz",
    "zf",
}


def _harsh_cluster_count(name: str) -> int:
    """Count harsh consonant clusters that are hard to pronounce."""
    name_lower = name.lower()
    count = 0
    for i in range(len(name_lower) - 1):
        bigram = name_lower[i : i + 2]
        if bigram in _HARSH_CLUSTERS:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Main composite scorer
# ---------------------------------------------------------------------------


@scorers.register(
    "brandability",
    description=(
        "Composite brandability score (0-1) combining pronounceability, "
        "novelty, visual balance, and phonetic appeal"
    ),
    cost="cheap",
    requires_network=False,
    latency="fast",
)
def brandability_score(name: str) -> float:
    """Compute a composite brandability score from 0 (poor) to 1 (excellent).

    Combines multiple weighted sub-scores:

    - **Pronounceability** (30%): syllable count sweet spot, vowel/consonant
      balance, no harsh clusters, spelling transparency
    - **Memorability** (25%): length sweet spot, letter variety, no boring
      repetition
    - **Novelty** (15%): not an existing common word
    - **Phonetic appeal** (15%): sound symbolism balance, positive morphemes
    - **Safety** (15%): no profanity substrings (hard filter: 0 if found)

    >>> 0.0 <= brandability_score('figiri') <= 1.0
    True
    """
    # Hard filter: profanity
    if _has_hazard(name):
        return 0.0

    # --- Pronounceability (30%) ---
    syllables = _syllable_count(name)
    # Sweet spot: 2-3 syllables
    if syllables in (2, 3):
        syl_score = 1.0
    elif syllables == 1:
        syl_score = 0.6
    elif syllables == 4:
        syl_score = 0.5
    else:
        syl_score = 0.2

    # Vowel/consonant balance (ideal 0.4-0.5)
    vc_ratio = _vowel_consonant_ratio(name)
    vc_score = 1.0 - min(1.0, abs(vc_ratio - 0.45) * 4)

    # Harsh clusters penalty
    harsh = _harsh_cluster_count(name)
    cluster_score = max(0.0, 1.0 - harsh * 0.4)

    # Spelling transparency
    spell_score = _spelling_transparency(name)

    pronounce = (
        0.35 * syl_score + 0.25 * vc_score + 0.2 * cluster_score + 0.2 * spell_score
    )

    # --- Memorability (25%) ---
    length = len(name)
    # Sweet spot: 5-7 chars
    if 5 <= length <= 7:
        len_score = 1.0
    elif length == 4 or length == 8:
        len_score = 0.7
    elif length == 3 or length == 9:
        len_score = 0.4
    else:
        len_score = 0.2

    # Letter variety
    variety = _unique_letter_ratio(name)
    # Sweet spot: 0.6-0.85 (some repetition is OK, too much variety is hard)
    if 0.6 <= variety <= 0.85:
        var_score = 1.0
    elif variety > 0.85:
        var_score = 0.7
    else:
        var_score = max(0.0, variety / 0.6)

    # Boring repetition penalty
    repeat_penalty = 0.0 if not _has_repeating_pattern(name) else 0.4

    memorability = 0.4 * len_score + 0.4 * var_score + 0.2 * (1.0 - repeat_penalty)

    # --- Novelty (15%) ---
    novel = _novelty(name)

    # --- Phonetic appeal (15%) ---
    morpheme = _positive_morpheme_score(name)

    # Sound symbolism: prefer balanced profile (not extreme)
    vowels_in = [c for c in name.lower() if c in _FRONT_VOWELS | _BACK_VOWELS]
    n_vowels = len(vowels_in) or 1
    front_r = sum(1 for v in vowels_in if v in _FRONT_VOWELS) / n_vowels
    # Balanced = good (not too extreme in either direction)
    balance = 1.0 - abs(front_r - 0.5) * 1.5
    balance = max(0.0, min(1.0, balance))

    appeal = 0.5 * morpheme + 0.5 * balance

    # --- Composite ---
    score = (
        0.30 * pronounce
        + 0.25 * memorability
        + 0.15 * novel
        + 0.15 * appeal
        + 0.15 * 1.0  # safety passed (hard filter above)
    )

    return round(max(0.0, min(1.0, score)), 4)
