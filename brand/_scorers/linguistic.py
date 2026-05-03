"""Linguistic and semantic scorers.

These scorers check for existing word collisions, cross-linguistic meanings,
profanity substrings, phonetic neighbors, novelty, and pronunciation entropy.
"""

import math
import re
from typing import NamedTuple

from brand.registry import scorers


# ---------------------------------------------------------------------------
# Novelty / word frequency
# ---------------------------------------------------------------------------


@scorers.register(
    "novelty",
    description="Novelty score via wordfreq (0=common word, 1=completely novel)",
)
def novelty_score(name: str) -> float:
    """Measure how novel a name is using word frequency data.

    Returns 1.0 for completely novel strings (not in any corpus),
    decreasing toward 0.0 for very common words.

    >>> novelty_score('the')  # very common
    0.0
    >>> novelty_score('xyzqwk')  # novel
    1.0
    """
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        raise ImportError(
            "Could not import 'wordfreq'. Install with: pip install wordfreq"
        )

    freq = zipf_frequency(name.lower(), "en")
    if freq == 0:
        return 1.0
    # Zipf scale: ~1 = very rare, ~7 = ultra common
    # Map to 0-1 where 1 = novel
    return max(0.0, round(1.0 - freq / 7.0, 3))


@scorers.register(
    "existing_word",
    description="Check if name is an existing English word (True=collision)",
)
def existing_word(name: str) -> bool:
    """Returns True if the name is a known English word (i.e., collision risk).

    >>> existing_word('apple')
    True
    >>> existing_word('xyzqwk')
    False
    """
    try:
        from wordfreq import zipf_frequency

        return zipf_frequency(name.lower(), "en") > 0
    except ImportError:
        # Fallback to lexis
        try:
            import lexis

            return name.lower() in lexis.Lemmas()
        except ImportError:
            return False


# ---------------------------------------------------------------------------
# Cross-linguistic safety
# ---------------------------------------------------------------------------


@scorers.register(
    "cross_linguistic",
    description="Check if name means something in major world languages",
    requires_network=True,
    latency="medium",
    cost="moderate",
)
def cross_linguistic_check(
    name: str,
    *,
    languages=("en", "es", "fr", "de", "pt", "it", "ja", "zh", "ar", "hi", "ru"),
) -> dict:
    """Check word frequency across multiple languages.

    Returns a dict mapping language codes to their zipf frequency.
    A frequency > 0 means the name is a known word in that language.
    """
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        return {"error": "wordfreq not installed"}

    flags = {}
    for lang in languages:
        freq = zipf_frequency(name.lower(), lang)
        if freq > 0:
            flags[lang] = round(freq, 2)
    return flags


# ---------------------------------------------------------------------------
# Substring hazards (profanity check)
# ---------------------------------------------------------------------------

# Common English profanity substrings to check (minimal built-in list).
# For thorough checking, use LDNOOBW or cuss data files.
_BUILTIN_BAD_SUBSTRINGS = {
    "ass",
    "damn",
    "hell",
    "shit",
    "fuck",
    "dick",
    "cock",
    "cunt",
    "piss",
    "slut",
    "whore",
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


@scorers.register(
    "substring_hazards",
    description="Scan for profanity substrings (window size 3-6)",
)
def substring_hazards(name: str, *, bad_words: set | None = None) -> list[str]:
    """Slide a window of length 3-6 over the name and check against profanity lists.

    Returns a list of found hazardous substrings (empty = clean).

    >>> substring_hazards('analytics')
    ['anal']
    >>> substring_hazards('figiri')
    []
    """
    if bad_words is None:
        bad_words = _BUILTIN_BAD_SUBSTRINGS

    name_lower = name.lower()
    found = []
    for window_size in range(3, 7):
        for i in range(len(name_lower) - window_size + 1):
            substr = name_lower[i : i + window_size]
            if substr in bad_words:
                found.append(substr)
    return sorted(set(found))


# ---------------------------------------------------------------------------
# Phonetic neighbors
# ---------------------------------------------------------------------------


@scorers.register(
    "phonetic_neighbors",
    description="Find words that sound like the name (Datamuse API)",
    requires_network=True,
    latency="medium",
    cost="moderate",
)
def phonetic_neighbors(name: str, *, max_results: int = 10) -> list[str]:
    """Query Datamuse for words that sound like *name*.

    >>> isinstance(phonetic_neighbors('brand'), list)
    True
    """
    import requests

    try:
        r = requests.get(
            "https://api.datamuse.com/words",
            params={"sl": name, "max": max_results},
            timeout=10,
        )
        r.raise_for_status()
        return [item["word"] for item in r.json()]
    except requests.RequestException:
        return []


# ---------------------------------------------------------------------------
# Spelling transparency
# ---------------------------------------------------------------------------

# Graphemes with multiple common pronunciations in English
_AMBIGUOUS_GRAPHEMES = {
    "c": 2,  # /k/ or /s/
    "g": 2,  # /g/ or /dʒ/
    "th": 2,  # /θ/ or /ð/
    "ough": 6,  # through, though, thought, rough, cough, bough
    "ch": 3,  # /tʃ/, /k/, /ʃ/
    "gh": 2,  # /g/, silent
    "ea": 3,  # /iː/, /ɛ/, /eɪ/
    "oo": 2,  # /uː/, /ʊ/
    "ou": 3,  # /aʊ/, /uː/, /ʌ/
    "x": 2,  # /ks/, /gz/
}


@scorers.register(
    "spelling_transparency",
    description="How unambiguously the name maps to one pronunciation",
)
def spelling_transparency(name: str) -> float:
    """Score spelling transparency from 0 (very ambiguous) to 1 (transparent).

    Counts grapheme-to-phoneme ambiguities and normalizes.

    >>> spelling_transparency('cat')  # very transparent
    1.0
    """
    name_lower = name.lower()
    ambiguity_score = 0

    for grapheme, n_pronunciations in _AMBIGUOUS_GRAPHEMES.items():
        count = name_lower.count(grapheme)
        if count > 0:
            ambiguity_score += count * (n_pronunciations - 1)

    # Normalize: each ambiguity point reduces transparency
    max_ambiguity = len(name_lower) * 2  # theoretical max
    if max_ambiguity == 0:
        return 1.0
    transparency = max(0.0, 1.0 - ambiguity_score / max_ambiguity)
    return round(transparency, 2)


# ---------------------------------------------------------------------------
# Pronunciation entropy
# ---------------------------------------------------------------------------

_VOWEL_CHARS = set("aeiouy")
_FRONT_VOWEL_CHARS = set("eiy")


class _GraphemeSpan(NamedTuple):
    grapheme: str
    start: int
    end: int
    position: str  # 'initial' | 'medial' | 'final' | 'sole'


# Positional ambiguity table: grapheme -> list of (condition, phone_distribution)
# conditions are dicts with keys: 'position', 'before', 'after', 'syllable'
# First matching rule wins. Last entry should be unconditional ({}).
_POSITIONAL_AMBIGUITY: dict[str, list[tuple[dict, dict[str, float]]]] = {
    # --- Vowels ---
    "y": [
        # Initial Y before consonant: highly ambiguous
        (
            {"position": "initial", "after": "consonant"},
            {"/j/": 0.10, "/aɪ/": 0.30, "/iː/": 0.25, "/ɪ/": 0.20, "silent": 0.15},
        ),
        # Initial Y before vowel: consonantal /j/
        ({"position": "initial", "after": "vowel"}, {"/j/": 0.95, "/iː/": 0.05}),
        # Terminal Y: almost always /iː/ in coined names
        ({"position": "final"}, {"/iː/": 0.85, "/aɪ/": 0.15}),
        # Medial Y between consonants
        (
            {"position": "medial", "before": "consonant", "after": "consonant"},
            {"/ɪ/": 0.50, "/aɪ/": 0.35, "/iː/": 0.15},
        ),
        # Unconditional fallback
        ({}, {"/iː/": 0.40, "/aɪ/": 0.30, "/ɪ/": 0.20, "/j/": 0.10}),
    ],
    "e": [
        # Terminal E after consonant: very ambiguous (silent? schwa?)
        (
            {"position": "final", "before": "consonant"},
            {"silent": 0.55, "/ə/": 0.20, "/ɛ/": 0.10, "/eɪ/": 0.10, "/iː/": 0.05},
        ),
        # Terminal E after vowel
        (
            {"position": "final"},
            {"silent": 0.40, "/ə/": 0.25, "/eɪ/": 0.15, "/ɛ/": 0.10, "/iː/": 0.10},
        ),
        # Initial E
        (
            {"position": "initial"},
            {"/ɛ/": 0.40, "/iː/": 0.30, "/ɪ/": 0.20, "/ə/": 0.10},
        ),
        # Medial E in open syllable
        (
            {"position": "medial", "syllable": "open"},
            {"/iː/": 0.45, "/ɛ/": 0.30, "/eɪ/": 0.15, "/ə/": 0.10},
        ),
        # Medial E in closed syllable
        (
            {"position": "medial", "syllable": "closed"},
            {"/ɛ/": 0.65, "/ɪ/": 0.15, "/iː/": 0.10, "/ə/": 0.10},
        ),
        # Unconditional
        ({}, {"/ɛ/": 0.50, "/iː/": 0.25, "/eɪ/": 0.15, "/ə/": 0.10}),
    ],
    "i": [
        # Initial I
        (
            {"position": "initial"},
            {"/ɪ/": 0.40, "/aɪ/": 0.35, "/iː/": 0.20, "/ə/": 0.05},
        ),
        # Medial I in open syllable
        (
            {"position": "medial", "syllable": "open"},
            {"/aɪ/": 0.50, "/iː/": 0.30, "/ɪ/": 0.20},
        ),
        # Medial I in closed syllable
        (
            {"position": "medial", "syllable": "closed"},
            {"/ɪ/": 0.70, "/aɪ/": 0.20, "/iː/": 0.10},
        ),
        # Unconditional
        ({}, {"/ɪ/": 0.50, "/aɪ/": 0.30, "/iː/": 0.15, "/ə/": 0.05}),
    ],
    "o": [
        # Initial O
        (
            {"position": "initial"},
            {"/ɒ/": 0.30, "/oʊ/": 0.35, "/ʌ/": 0.15, "/uː/": 0.10, "/ə/": 0.10},
        ),
        # Terminal O
        ({"position": "final"}, {"/oʊ/": 0.75, "/uː/": 0.15, "/ə/": 0.10}),
        # Medial O in open syllable
        (
            {"position": "medial", "syllable": "open"},
            {"/oʊ/": 0.55, "/ɒ/": 0.25, "/uː/": 0.10, "/ə/": 0.10},
        ),
        # Medial O in closed syllable
        (
            {"position": "medial", "syllable": "closed"},
            {"/ɒ/": 0.55, "/oʊ/": 0.20, "/ʌ/": 0.15, "/ə/": 0.10},
        ),
        # Unconditional
        ({}, {"/ɒ/": 0.35, "/oʊ/": 0.35, "/ʌ/": 0.15, "/ə/": 0.15}),
    ],
    "a": [
        # Terminal A
        ({"position": "final"}, {"/ɑː/": 0.60, "/ə/": 0.30, "/æ/": 0.10}),
        # Medial A in open syllable
        (
            {"position": "medial", "syllable": "open"},
            {"/eɪ/": 0.50, "/æ/": 0.30, "/ɑː/": 0.20},
        ),
        # Medial A in closed syllable
        (
            {"position": "medial", "syllable": "closed"},
            {"/æ/": 0.65, "/eɪ/": 0.15, "/ɑː/": 0.15, "/ə/": 0.05},
        ),
        # Unconditional
        ({}, {"/æ/": 0.40, "/eɪ/": 0.25, "/ɑː/": 0.25, "/ə/": 0.10}),
    ],
    "u": [
        # Terminal U
        ({"position": "final"}, {"/uː/": 0.70, "/juː/": 0.20, "/ə/": 0.10}),
        # Unconditional
        ({}, {"/ʌ/": 0.40, "/uː/": 0.30, "/juː/": 0.15, "/ʊ/": 0.10, "/ə/": 0.05}),
    ],
    # --- Consonants with positional ambiguity ---
    "c": [
        ({"after": "front_vowel"}, {"/s/": 0.85, "/k/": 0.15}),
        ({}, {"/k/": 0.85, "/s/": 0.10, "/tʃ/": 0.05}),
    ],
    "g": [
        ({"after": "front_vowel"}, {"/dʒ/": 0.55, "/g/": 0.40, "/ʒ/": 0.05}),
        ({}, {"/g/": 0.90, "/dʒ/": 0.10}),
    ],
    "s": [
        # Intervocalic S
        (
            {"before": "vowel", "after": "vowel"},
            {"/s/": 0.50, "/z/": 0.45, "/ʒ/": 0.05},
        ),
        ({}, {"/s/": 0.90, "/z/": 0.08, "/ʃ/": 0.02}),
    ],
    "x": [
        ({"position": "initial"}, {"/z/": 0.80, "/ks/": 0.15, "/ʃ/": 0.05}),
        ({}, {"/ks/": 0.75, "/gz/": 0.20, "/z/": 0.05}),
    ],
    # --- Digraphs ---
    "th": [({}, {"/θ/": 0.55, "/ð/": 0.40, "/t/": 0.05})],
    "ch": [({}, {"/tʃ/": 0.60, "/k/": 0.25, "/ʃ/": 0.15})],
    "gh": [
        ({"position": "initial"}, {"/g/": 0.95, "silent": 0.05}),
        ({}, {"silent": 0.50, "/f/": 0.35, "/g/": 0.15}),
    ],
    "ph": [({}, {"/f/": 0.95, "/p/": 0.05})],
    "sh": [({}, {"/ʃ/": 0.98, "/s.h/": 0.02})],
    # --- Vowel digraphs ---
    "ea": [({}, {"/iː/": 0.50, "/ɛ/": 0.30, "/eɪ/": 0.20})],
    "oo": [({}, {"/uː/": 0.65, "/ʊ/": 0.30, "/ʌ/": 0.05})],
    "ou": [({}, {"/aʊ/": 0.40, "/uː/": 0.25, "/ʌ/": 0.20, "/oʊ/": 0.15})],
    "ei": [({}, {"/eɪ/": 0.45, "/iː/": 0.30, "/aɪ/": 0.25})],
    "ee": [({}, {"/iː/": 0.98, "/eɪ/": 0.02})],
}

# Digraphs to check before single letters (longest-match tokenization)
_DIGRAPHS = sorted(
    [g for g in _POSITIONAL_AMBIGUITY if len(g) > 1],
    key=len,
    reverse=True,
)

# Cross-linguistic overrides: language -> grapheme -> rules
_CROSS_LINGUISTIC_OVERRIDES: dict[
    str, dict[str, list[tuple[dict, dict[str, float]]]]
] = {
    "fr": {
        "e": [
            # French terminal E is /ə/ (not silent)
            ({"position": "final"}, {"/ə/": 0.75, "/ɛ/": 0.15, "silent": 0.10}),
            ({}, {"/ə/": 0.40, "/ɛ/": 0.35, "/e/": 0.25}),
        ],
        "u": [
            # French U = /y/ (front rounded)
            ({}, {"/y/": 0.80, "/u/": 0.15, "/ə/": 0.05}),
        ],
        "i": [
            # French I = /i/, no long-i /aɪ/
            ({}, {"/i/": 0.90, "/ɪ/": 0.10}),
        ],
        "y": [
            # French Y = /i/ in most positions
            (
                {"position": "initial", "after": "consonant"},
                {"/i/": 0.70, "/j/": 0.20, "silent": 0.10},
            ),
            ({}, {"/i/": 0.85, "/j/": 0.15}),
        ],
        "a": [
            # French A = /a/, very stable
            ({}, {"/a/": 0.85, "/ɑ/": 0.15}),
        ],
        "o": [
            # French O = /o/ or /ɔ/, no diphthong
            ({"position": "final"}, {"/o/": 0.80, "/ɔ/": 0.20}),
            ({}, {"/ɔ/": 0.50, "/o/": 0.45, "/ə/": 0.05}),
        ],
        "ou": [({}, {"/u/": 0.90, "/uː/": 0.10})],
        "ch": [({}, {"/ʃ/": 0.90, "/k/": 0.10})],
    },
}


def _is_vowel_char(c: str) -> bool:
    return c.lower() in _VOWEL_CHARS


def _tokenize_graphemes(name: str) -> list[_GraphemeSpan]:
    """Tokenize *name* into grapheme spans using longest-match on digraphs."""
    name_lower = name.lower()
    spans: list[_GraphemeSpan] = []
    i = 0
    while i < len(name_lower):
        c = name_lower[i]
        if not c.isalpha():
            i += 1
            continue
        matched = False
        for digraph in _DIGRAPHS:
            if name_lower[i : i + len(digraph)] == digraph:
                spans.append(_GraphemeSpan(digraph, i, i + len(digraph), ""))
                i += len(digraph)
                matched = True
                break
        if not matched:
            spans.append(_GraphemeSpan(c, i, i + 1, ""))
            i += 1

    # Assign positions
    result = []
    for idx, span in enumerate(spans):
        if len(spans) == 1:
            pos = "sole"
        elif idx == 0:
            pos = "initial"
        elif idx == len(spans) - 1:
            pos = "final"
        else:
            pos = "medial"
        result.append(span._replace(position=pos))
    return result


def _classify_context(
    spans: list[_GraphemeSpan],
    idx: int,
    name: str,
) -> dict:
    """Build a context dict for the grapheme span at *idx*."""
    name_lower = name.lower()
    span = spans[idx]
    ctx: dict[str, str] = {"position": span.position}

    # What comes before?
    if idx > 0:
        prev_char = name_lower[spans[idx - 1].end - 1]
        if _is_vowel_char(prev_char):
            ctx["before"] = "vowel"
        else:
            ctx["before"] = "consonant"
    else:
        ctx["before"] = "boundary"

    # What comes after?
    if idx < len(spans) - 1:
        next_char = name_lower[spans[idx + 1].start]
        if next_char in _FRONT_VOWEL_CHARS:
            ctx["after"] = "front_vowel"
        elif _is_vowel_char(next_char):
            ctx["after"] = "vowel"
        else:
            ctx["after"] = "consonant"
    else:
        ctx["after"] = "boundary"

    # Syllable structure (for vowel graphemes only)
    grapheme_lower = span.grapheme.lower()
    if any(c in _VOWEL_CHARS for c in grapheme_lower):
        # Count consonants between this vowel and the next vowel (or end)
        consonants_after = 0
        found_next_vowel = False
        for j in range(idx + 1, len(spans)):
            g = spans[j].grapheme.lower()
            if any(c in _VOWEL_CHARS for c in g):
                found_next_vowel = True
                break
            consonants_after += 1

        if not found_next_vowel:
            # At or near end of word
            ctx["syllable"] = "closed" if consonants_after > 0 else "open"
        elif consonants_after <= 1:
            # Maximal onset principle: single consonant before next vowel
            ctx["syllable"] = "open"
        else:
            ctx["syllable"] = "closed"

    return ctx


def _match_rule(context: dict, condition: dict) -> bool:
    """Return True if all condition keys match the context.

    Special handling: ``'after': 'front_vowel'`` in a condition also
    matches ``context['after'] == 'front_vowel'``; and ``'after': 'vowel'``
    in a condition matches ``'vowel'`` or ``'front_vowel'`` in context.
    """
    for key, val in condition.items():
        ctx_val = context.get(key)
        if ctx_val is None:
            return False
        if val == "vowel" and key == "after":
            if ctx_val not in ("vowel", "front_vowel"):
                return False
        elif ctx_val != val:
            return False
    return True


def _shannon_entropy(dist: dict[str, float]) -> float:
    """Shannon entropy in bits."""
    return -sum(p * math.log2(p) for p in dist.values() if p > 0)


def _get_distribution(
    grapheme: str,
    context: dict,
    table: dict,
) -> dict[str, float] | None:
    """Look up the phone distribution for *grapheme* in *table*."""
    rules = table.get(grapheme)
    if rules is None:
        return None
    for condition, dist in rules:
        if _match_rule(context, condition):
            return dist
    return None


def _merge_distributions(dists: list[dict[str, float]]) -> dict[str, float]:
    """Merge multiple phone distributions by averaging and re-normalizing."""
    if len(dists) == 1:
        return dists[0]
    all_phones: set[str] = set()
    for d in dists:
        all_phones.update(d.keys())
    merged = {}
    for phone in all_phones:
        merged[phone] = sum(d.get(phone, 0.0) for d in dists) / len(dists)
    # Re-normalize
    total = sum(merged.values())
    if total > 0:
        merged = {k: v / total for k, v in merged.items()}
    return merged


@scorers.register(
    "pronunciation_entropy",
    description="Pronunciation ambiguity in bits (0=unambiguous, higher=more ambiguous)",
)
def pronunciation_entropy(
    name: str,
    *,
    languages: tuple[str, ...] = ("en",),
) -> float:
    """Measure grapheme-to-phoneme ambiguity as Shannon entropy in bits.

    Unlike ``spelling_transparency`` which uses a flat lookup of ambiguous
    graphemes, this scorer models **positional and contextual** ambiguity:
    initial Y before a consonant is highly ambiguous, terminal Y is not;
    terminal E is ambiguous (silent? schwa?), medial E less so; vowels
    in open vs. closed syllables have different probability distributions.

    Parameters
    ----------
    name : str
        The candidate brand name.
    languages : tuple[str, ...]
        Target languages for cross-linguistic entropy.  Default ``('en',)``
        uses English-only rules.  Pass ``('en', 'fr')`` to include French
        reading ambiguity (merged distribution, higher entropy when the
        languages disagree on pronunciation).

    Returns
    -------
    float
        Shannon entropy in bits, where 0.0 = completely unambiguous and
        higher values indicate more pronunciation ambiguity.  Typical
        range for 6-letter coined names: 1.0 -- 6.0 bits.

    Examples
    --------
    >>> pronunciation_entropy('panapy') < pronunciation_entropy('ysolos')
    True
    >>> pronunciation_entropy('bab') < pronunciation_entropy('levole')
    True
    """
    if not name:
        return 0.0

    spans = _tokenize_graphemes(name)
    if not spans:
        return 0.0

    total_entropy = 0.0
    for idx, span in enumerate(spans):
        context = _classify_context(spans, idx, name)
        grapheme = span.grapheme.lower()

        # Collect distributions from each target language
        lang_dists: list[dict[str, float]] = []

        # English (always the base)
        en_dist = _get_distribution(grapheme, context, _POSITIONAL_AMBIGUITY)
        if en_dist is not None:
            lang_dists.append(en_dist)

        # Additional languages
        for lang in languages:
            if lang == "en":
                continue
            overrides = _CROSS_LINGUISTIC_OVERRIDES.get(lang, {})
            lang_dist = _get_distribution(grapheme, context, overrides)
            if lang_dist is not None:
                lang_dists.append(lang_dist)
            elif en_dist is not None:
                # Fall back to English distribution for this language
                lang_dists.append(en_dist)

        if not lang_dists:
            # Grapheme not in any table -> unambiguous consonant
            continue

        merged = _merge_distributions(lang_dists)
        total_entropy += _shannon_entropy(merged)

    return round(total_entropy, 3)


def pronunciation_entropy_detail(
    name: str,
    *,
    languages: tuple[str, ...] = ("en",),
) -> list[dict]:
    """Return per-grapheme entropy breakdown for debugging and exploration.

    Returns a list of dicts with keys: ``grapheme``, ``position``,
    ``context``, ``distribution``, ``entropy_bits``.
    """
    if not name:
        return []

    spans = _tokenize_graphemes(name)
    details = []
    for idx, span in enumerate(spans):
        context = _classify_context(spans, idx, name)
        grapheme = span.grapheme.lower()

        lang_dists: list[dict[str, float]] = []
        en_dist = _get_distribution(grapheme, context, _POSITIONAL_AMBIGUITY)
        if en_dist is not None:
            lang_dists.append(en_dist)
        for lang in languages:
            if lang == "en":
                continue
            overrides = _CROSS_LINGUISTIC_OVERRIDES.get(lang, {})
            lang_dist = _get_distribution(grapheme, context, overrides)
            if lang_dist is not None:
                lang_dists.append(lang_dist)
            elif en_dist is not None:
                lang_dists.append(en_dist)

        if not lang_dists:
            merged = {}
            entropy = 0.0
        else:
            merged = _merge_distributions(lang_dists)
            entropy = _shannon_entropy(merged)

        details.append(
            {
                "grapheme": grapheme,
                "position": span.position,
                "context": context,
                "distribution": {k: round(v, 3) for k, v in merged.items()},
                "entropy_bits": round(entropy, 3),
            }
        )
    return details
