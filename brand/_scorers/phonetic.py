"""Phonetic and phonolinguistic scorers.

Scorers in this module measure how a name *sounds*: phonotactic legality,
syllable count, stress patterns, articulatory complexity, and sound symbolism
profile.

Optional dependencies
---------------------
- ``pronouncing`` — CMU dictionary lookups (syllables, stress)
- ``python-BLICK`` — phonotactic well-formedness
- ``epitran`` + ``panphon`` — IPA transcription and articulatory features
"""

from brand.registry import scorers

# ---------------------------------------------------------------------------
# Helpers (lazy imports to handle optional deps gracefully)
# ---------------------------------------------------------------------------

_EXTRAS_MSG = (
    "This scorer requires the 'phonetics' extra. "
    "Install with: pip install brand[phonetics]"
)


def _require(package_name):
    """Import and return a package, raising an informative error on failure."""
    import importlib

    try:
        return importlib.import_module(package_name)
    except ImportError:
        raise ImportError(f"Could not import {package_name!r}. {_EXTRAS_MSG}")


def _get_arpabet(name: str) -> list[str] | None:
    """Get ARPAbet phones for *name* from the CMU dict, or None."""
    pronouncing = _require('pronouncing')
    phones_list = pronouncing.phones_for_word(name.lower())
    if phones_list:
        return phones_list[0].split()
    return None


def _get_ipa(name: str, lang='eng-Latn') -> str:
    """Transliterate *name* to IPA using epitran."""
    epitran = _require('epitran')
    epi = epitran.Epitran(lang)
    return epi.transliterate(name.lower())


# ---------------------------------------------------------------------------
# Scorers
# ---------------------------------------------------------------------------


@scorers.register(
    'syllables',
    description='Count syllables (via CMU dict or vowel heuristic)',
)
def syllable_count(name: str) -> int:
    """Count syllables in *name*.

    Uses CMU Pronouncing Dictionary when the word is known; falls back to a
    simple vowel-counting heuristic for novel coinages.

    >>> syllable_count('banana')
    3
    >>> syllable_count('strength')
    1
    """
    try:
        pronouncing = _require('pronouncing')
        phones_list = pronouncing.phones_for_word(name.lower())
        if phones_list:
            return pronouncing.syllable_count(phones_list[0])
    except ImportError:
        pass
    # Fallback: count vowel groups
    import re

    vowel_groups = re.findall(r'[aeiouy]+', name.lower())
    count = len(vowel_groups)
    # Adjust for silent-e at end
    if name.lower().endswith('e') and count > 1:
        count -= 1
    return max(1, count)


@scorers.register(
    'stress_pattern',
    description='Extract stress pattern (e.g. "10" = trochaic)',
)
def stress_pattern(name: str) -> str:
    """Return the stress digit string (1=primary, 2=secondary, 0=unstressed).

    Returns ``'unknown'`` if the word is not in the CMU dictionary.

    >>> stress_pattern('hello')
    '01'
    """
    try:
        pronouncing = _require('pronouncing')
        phones_list = pronouncing.phones_for_word(name.lower())
        if phones_list:
            return pronouncing.stresses(phones_list[0])
    except ImportError:
        pass
    return 'unknown'


@scorers.register(
    'phonotactic',
    description='BLICK phonotactic well-formedness (0=perfect, higher=worse)',
    requires_extras=('python-BLICK',),
)
def phonotactic_score(name: str) -> float:
    """Compute BLICK phonotactic well-formedness score.

    A score of 0 means the name obeys all English phonotactic constraints
    perfectly.  Higher scores indicate increasingly ill-formed sequences.
    """
    blick = _require('blick')
    try:
        result = blick.blick(name.lower())
        if result is not None:
            # blick returns (score, details) or just a number depending on version
            if isinstance(result, (list, tuple)):
                return float(result[0])
            return float(result)
    except Exception:
        pass
    return -1.0  # sentinel: could not compute


@scorers.register(
    'articulatory_complexity',
    description='Count place-of-articulation transitions between consonants',
    requires_extras=('epitran', 'panphon'),
)
def articulatory_complexity(name: str) -> float:
    """Measure articulatory complexity as mean feature distance between
    consecutive consonant segments.

    Lower values = easier to pronounce.  Returns -1 if deps are missing.
    """
    try:
        epitran_mod = _require('epitran')
        panphon = _require('panphon')
    except ImportError:
        return -1.0

    epi = epitran_mod.Epitran('eng-Latn')
    ft = panphon.FeatureTable()

    ipa = epi.transliterate(name.lower())
    segments = ft.ipa_segs(ipa)

    if len(segments) < 2:
        return 0.0

    # Compute mean feature distance between consecutive segments
    distances = []
    for a, b in zip(segments[:-1], segments[1:]):
        d = ft.fts(a).hamming_distance(ft.fts(b))
        distances.append(d)

    return sum(distances) / len(distances) if distances else 0.0


@scorers.register(
    'sound_symbolism',
    description='Sound symbolism profile (front/back vowel ratio, stop/fricative ratio)',
    requires_extras=('epitran', 'panphon'),
)
def sound_symbolism(name: str) -> dict:
    """Compute a sound symbolism profile based on Klink (2000).

    Returns a dict with keys:
    - ``front_vowel_ratio``: proportion of front vowels (→ small/fast/precise)
    - ``back_vowel_ratio``: proportion of back vowels (→ large/powerful/warm)
    - ``voiceless_ratio``: proportion of voiceless consonants (→ sharp/clean)
    - ``voiced_ratio``: proportion of voiced consonants (→ heavy/strong)
    - ``profile``: one of 'modern/sharp', 'warm/powerful', 'balanced', 'neutral'
    """
    # Simple heuristic based on letter classification (no deps required)
    name_lower = name.lower()

    front_vowels = set('eiy')
    back_vowels = set('oua')
    voiceless = set('ptksfc')
    voiced = set('bdgvzjmnlr')

    vowels_in_name = [c for c in name_lower if c in front_vowels | back_vowels]
    consonants_in_name = [c for c in name_lower if c in voiceless | voiced]

    n_vowels = len(vowels_in_name) or 1
    n_consonants = len(consonants_in_name) or 1

    front_ratio = sum(1 for v in vowels_in_name if v in front_vowels) / n_vowels
    back_ratio = sum(1 for v in vowels_in_name if v in back_vowels) / n_vowels
    voiceless_ratio = (
        sum(1 for c in consonants_in_name if c in voiceless) / n_consonants
    )
    voiced_ratio = (
        sum(1 for c in consonants_in_name if c in voiced) / n_consonants
    )

    # Determine dominant profile
    if front_ratio > 0.6 and voiceless_ratio > 0.5:
        profile = 'modern/sharp'
    elif back_ratio > 0.6 and voiced_ratio > 0.5:
        profile = 'warm/powerful'
    elif front_ratio > 0.5 or voiceless_ratio > 0.5:
        profile = 'balanced/modern'
    elif back_ratio > 0.5 or voiced_ratio > 0.5:
        profile = 'balanced/warm'
    else:
        profile = 'neutral'

    return {
        'front_vowel_ratio': round(front_ratio, 2),
        'back_vowel_ratio': round(back_ratio, 2),
        'voiceless_ratio': round(voiceless_ratio, 2),
        'voiced_ratio': round(voiced_ratio, 2),
        'profile': profile,
    }
