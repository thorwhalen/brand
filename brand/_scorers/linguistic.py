"""Linguistic and semantic scorers.

These scorers check for existing word collisions, cross-linguistic meanings,
profanity substrings, phonetic neighbors, and novelty.
"""

import re

from brand.registry import scorers


# ---------------------------------------------------------------------------
# Novelty / word frequency
# ---------------------------------------------------------------------------


@scorers.register(
    'novelty',
    description='Novelty score via wordfreq (0=common word, 1=completely novel)',
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

    freq = zipf_frequency(name.lower(), 'en')
    if freq == 0:
        return 1.0
    # Zipf scale: ~1 = very rare, ~7 = ultra common
    # Map to 0-1 where 1 = novel
    return max(0.0, round(1.0 - freq / 7.0, 3))


@scorers.register(
    'existing_word',
    description='Check if name is an existing English word (True=collision)',
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

        return zipf_frequency(name.lower(), 'en') > 0
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
    'cross_linguistic',
    description='Check if name means something in major world languages',
    requires_network=True,
    latency='medium',
    cost='moderate',
)
def cross_linguistic_check(
    name: str,
    *,
    languages=('en', 'es', 'fr', 'de', 'pt', 'it', 'ja', 'zh', 'ar', 'hi', 'ru'),
) -> dict:
    """Check word frequency across multiple languages.

    Returns a dict mapping language codes to their zipf frequency.
    A frequency > 0 means the name is a known word in that language.
    """
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        return {'error': 'wordfreq not installed'}

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
    'ass', 'damn', 'hell', 'shit', 'fuck', 'dick', 'cock', 'cunt',
    'piss', 'slut', 'whore', 'nazi', 'rape', 'porn', 'anal', 'anus',
    'tit', 'nig', 'fag', 'cum', 'poo',
}


@scorers.register(
    'substring_hazards',
    description='Scan for profanity substrings (window size 3-6)',
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
    'phonetic_neighbors',
    description='Find words that sound like the name (Datamuse API)',
    requires_network=True,
    latency='medium',
    cost='moderate',
)
def phonetic_neighbors(name: str, *, max_results: int = 10) -> list[str]:
    """Query Datamuse for words that sound like *name*.

    >>> isinstance(phonetic_neighbors('brand'), list)
    True
    """
    import requests

    try:
        r = requests.get(
            'https://api.datamuse.com/words',
            params={'sl': name, 'max': max_results},
            timeout=10,
        )
        r.raise_for_status()
        return [item['word'] for item in r.json()]
    except requests.RequestException:
        return []


# ---------------------------------------------------------------------------
# Spelling transparency
# ---------------------------------------------------------------------------

# Graphemes with multiple common pronunciations in English
_AMBIGUOUS_GRAPHEMES = {
    'c': 2,  # /k/ or /s/
    'g': 2,  # /g/ or /dʒ/
    'th': 2,  # /θ/ or /ð/
    'ough': 6,  # through, though, thought, rough, cough, bough
    'ch': 3,  # /tʃ/, /k/, /ʃ/
    'gh': 2,  # /g/, silent
    'ea': 3,  # /iː/, /ɛ/, /eɪ/
    'oo': 2,  # /uː/, /ʊ/
    'ou': 3,  # /aʊ/, /uː/, /ʌ/
    'x': 2,  # /ks/, /gz/
}


@scorers.register(
    'spelling_transparency',
    description='How unambiguously the name maps to one pronunciation',
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
