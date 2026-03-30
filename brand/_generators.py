"""Name generators: combinatoric, morpheme-based, AI-assisted, and from-list.

Each generator is a function that returns an iterable of candidate name strings.
Generators are registered in the global ``generators`` registry.
"""

import itertools
import re
from collections.abc import Iterable

from brand.registry import generators


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VOWELS = "aeiouy"
CONSONANTS = "bcdfghjklmnpqrstvwxz"
FEWER_CONSONANTS = "bdfglmnprstvz"

_VOWELS_SET = set(VOWELS)
_CONSONANTS_SET = set(CONSONANTS)


# ---------------------------------------------------------------------------
# Filter helpers (used as default pre-filters for generators)
# ---------------------------------------------------------------------------


def few_uniques(w, *, max_uniques=4, max_unique_vowels=1, max_unique_consonants=1):
    """Keep names with limited unique letters and constrained vowel/consonant variety.

    >>> few_uniques('bababa')
    True
    >>> few_uniques('abcdef')
    False
    """
    letters = set(w)
    if len(letters) > max_uniques:
        return False
    return (
        len(letters & _VOWELS_SET) <= max_unique_vowels
        or len(letters & _CONSONANTS_SET) <= max_unique_consonants
    )


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


@generators.register(
    "cvcvcv",
    description="Generate all 6-letter consonant-vowel-consonant-vowel-consonant-vowel names",
)
def cvcvcv(
    *,
    consonants: str = FEWER_CONSONANTS,
    vowels: str = VOWELS,
    filt=None,
) -> Iterable[str]:
    """Generate CVCVCV combinations.

    >>> names = list(cvcvcv(consonants='b', vowels='a'))
    >>> names
    ['bababa']
    """
    gen = map(
        "".join,
        itertools.product(consonants, vowels, consonants, vowels, consonants, vowels),
    )
    if filt is not None:
        gen = filter(filt, gen)
    return gen


@generators.register(
    "cvcvcv_filtered",
    description="CVCVCV names pre-filtered for few unique letters",
)
def cvcvcv_filtered(
    *,
    consonants: str = FEWER_CONSONANTS,
    vowels: str = VOWELS,
) -> Iterable[str]:
    """CVCVCV with the ``few_uniques`` filter applied.

    >>> names = list(cvcvcv_filtered(consonants='bd', vowels='ae'))
    >>> 'bababa' in names
    True
    """
    return cvcvcv(consonants=consonants, vowels=vowels, filt=few_uniques)


@generators.register(
    "pattern",
    description='Generate names matching a CV pattern (e.g. "CVCCV")',
)
def pattern_generator(
    *,
    pattern: str = "CVCVCV",
    consonants: str = FEWER_CONSONANTS,
    vowels: str = VOWELS,
    filt=None,
) -> Iterable[str]:
    """Generate all names matching a consonant/vowel pattern.

    ``C`` = consonant, ``V`` = vowel.

    >>> len(list(pattern_generator(pattern='CV', consonants='b', vowels='a')))
    1
    """
    pools = []
    for char in pattern.upper():
        if char == "C":
            pools.append(consonants)
        elif char == "V":
            pools.append(vowels)
        else:
            raise ValueError(f"Pattern must contain only 'C' and 'V', got {char!r}")

    gen = map("".join, itertools.product(*pools))
    if filt is not None:
        gen = filter(filt, gen)
    return gen


@generators.register(
    "english_words",
    description="English dictionary words filtered by regex",
)
def english_words(*, pattern: str = ".*") -> Iterable[str]:
    """Generate English words matching a regex pattern.

    >>> 'cat' in list(english_words(pattern='^cat$'))
    True
    """
    import lexis

    compiled = re.compile(pattern)
    return filter(compiled.search, lexis.Lemmas())


@generators.register(
    "from_list",
    description="Load names from an explicit list",
)
def from_list(*, names: list[str]) -> Iterable[str]:
    """Simply yield the provided names.

    >>> list(from_list(names=['alpha', 'beta']))
    ['alpha', 'beta']
    """
    return iter(names)


@generators.register(
    "from_file",
    description="Load names from a text file (one per line)",
)
def from_file(*, path: str) -> Iterable[str]:
    """Read names from a file, one name per line, stripping whitespace."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield line


@generators.register(
    "ai_suggest",
    cost="expensive",
    requires_network=True,
    latency="slow",
    description="AI-assisted name generation via OpenAI",
)
def ai_suggest(*, context: str, n: int = 30) -> Iterable[str]:
    """Use an LLM to brainstorm brand names for a given context.

    Requires the ``oa`` package and an OpenAI API key.
    """
    try:
        import oa
    except ImportError:
        raise ImportError(
            "AI generation requires the 'oa' package. Install with: pip install oa"
        )

    ask_fn = oa.prompt_function(
        "You are an expert brand namer. Suggest {n} creative, memorable brand "
        "names (1-15 characters each) for: {context}\n\n"
        "Output ONLY the names, one per line, no numbering or explanation."
    )
    response = ask_fn(context=context, n=n)
    names = [line.strip() for line in response.strip().split("\n") if line.strip()]
    return names


@generators.register(
    "morpheme_combiner",
    description="Combine morpheme roots to create brand-like portmanteaus",
)
def morpheme_combiner(
    *,
    prefixes: list[str] | None = None,
    suffixes: list[str] | None = None,
) -> Iterable[str]:
    """Combine prefix and suffix morphemes to generate portmanteau-style names.

    >>> sorted(morpheme_combiner(prefixes=['lum'], suffixes=['ix', 'ify']))
    ['lumify', 'lumix']
    """
    if prefixes is None:
        prefixes = [
            "lum",
            "clar",
            "vox",
            "flux",
            "syn",
            "lex",
            "pho",
            "zen",
            "arc",
            "neo",
            "axi",
            "ori",
            "sol",
            "nex",
            "val",
            "ver",
            "alt",
            "cor",
            "prim",
            "evo",
            "gen",
            "vis",
            "aur",
            "tel",
        ]
    if suffixes is None:
        suffixes = [
            "ify",
            "ix",
            "io",
            "us",
            "is",
            "ia",
            "eo",
            "ar",
            "um",
            "os",
            "al",
            "en",
            "yx",
            "on",
            "or",
            "ux",
            "ive",
            "ent",
        ]

    for prefix, suffix in itertools.product(prefixes, suffixes):
        yield prefix + suffix
