"""Phonotactic families: inventories, a prompt template and a validator.

Naming by sound works best when an LLM composes names *within* a phonotactic
family (Japanese-like CV, Finnic vowel harmony, Bantu prenasalised onsets...)
and a deterministic validator then rejects whatever strays outside it. This
module provides both halves; it makes no network call itself.

>>> validate_phonotactic('kimono', 'japanese_cv')
True
>>> validate_phonotactic('strik', 'japanese_cv')
False
>>> validate_phonotactic('mbalo', 'bantu_prenasalised')
True
>>> validate_phonotactic('tolyva', 'finnic_harmony')  # back 'o','a' + front 'y'
False
>>> 'japanese_cv' in PHONOTACTIC_FAMILIES
True
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from brand.registry import generators


@dataclass(frozen=True)
class PhonotacticFamily:
    """Inventory defining the legal names of a phonotactic family.

    A name is a sequence of syllables ``onset? + vowel + coda?`` drawn from
    the inventory. ``harmony`` lists vowel groups; a name may use vowels from at
    most one group that is not listed in ``neutral``.
    """

    onsets: tuple[str, ...]
    vowels: tuple[str, ...]
    codas: tuple[str, ...] = ()
    description: str = ""
    harmony: tuple[str, ...] = field(default_factory=tuple)  # e.g. ("aou", "yäö")
    neutral: str = ""
    min_syllables: int = 2
    max_syllables: int = 4


PHONOTACTIC_FAMILIES: Mapping[str, PhonotacticFamily] = {
    "japanese_cv": PhonotacticFamily(
        onsets=tuple("k s t n h m y r w g z d b p".split())
        + ("sh", "ch", "ts", "j", "f"),
        vowels=tuple("aeiou"),
        codas=("n",),
        description="Japanese-like: open CV syllables, optional moraic final n",
    ),
    "finnic_harmony": PhonotacticFamily(
        onsets=tuple("k l m n p r s t v h j".split()),
        vowels=tuple("aeiouyäö"),
        codas=("n", "l", "r", "s", "t"),
        description="Finnic-like: simple onsets, front/back vowel harmony",
        harmony=("aou", "yäö"),
        neutral="ei",
    ),
    "bantu_prenasalised": PhonotacticFamily(
        onsets=tuple("b d g k l m n p s t v z".split())
        + ("mb", "nd", "ng", "nj", "nk", "nt", "ny"),
        vowels=tuple("aeiou"),
        description="Bantu-like: strictly open syllables, prenasalised onsets",
    ),
}


def _family(family) -> PhonotacticFamily:
    if isinstance(family, PhonotacticFamily):
        return family
    try:
        return PHONOTACTIC_FAMILIES[family]
    except KeyError:
        raise KeyError(
            f"Unknown phonotactic family {family!r}; "
            f"choose from {sorted(PHONOTACTIC_FAMILIES)}"
        ) from None


def _alt(items: Iterable[str]) -> str:
    return "|".join(re.escape(x) for x in sorted(items, key=len, reverse=True))


def _name_regex(fam: PhonotacticFamily) -> re.Pattern:
    syllable = f"(?:(?:{_alt(fam.onsets)})?(?:{_alt(fam.vowels)})"
    if fam.codas:
        syllable += f"(?:{_alt(fam.codas)})?"
    syllable += ")"
    return re.compile(f"^{syllable}{{{fam.min_syllables},{fam.max_syllables}}}$")


def validate_phonotactic(name: str, family="japanese_cv") -> bool:
    """Return True if ``name`` is a legal name of the phonotactic ``family``.

    ``family`` is a key of ``PHONOTACTIC_FAMILIES`` or a ``PhonotacticFamily``.
    """
    fam = _family(family)
    name = name.lower()
    if not _name_regex(fam).match(name):
        return False
    if fam.harmony:
        groups = {
            i
            for i, group in enumerate(fam.harmony)
            for ch in name
            if ch in group and ch not in fam.neutral
        }
        if len(groups) > 1:
            return False
    return True


PHONOTACTIC_PROMPT = (
    "You are a brand namer working strictly within one phonotactic family: "
    "{family} ({description}).\n"
    "Rules: each name is {min_syllables}-{max_syllables} syllables of the form "
    "[onset]vowel[coda]. Allowed onsets: {onsets}. Allowed vowels: {vowels}. "
    "Allowed codas: {codas}.{harmony}\n"
    "Compose {n} pronounceable, memorable names that feel native to this "
    "family, are not real words in major languages, and suit: {context}\n\n"
    "Output ONLY the names, lowercase, one per line, no numbering or explanation."
)


def phonotactic_prompt(family="japanese_cv", *, context: str, n: int = 50) -> str:
    """Build the LLM prompt asking for ``n`` names within ``family``."""
    fam = _family(family)
    name = family if isinstance(family, str) else "custom"
    harmony = ""
    if fam.harmony:
        harmony = (
            f" Vowel harmony: use vowels from only one of {list(fam.harmony)} "
            f"(neutral vowels {fam.neutral!r} combine with either)."
        )
    return PHONOTACTIC_PROMPT.format(
        family=name,
        description=fam.description,
        min_syllables=fam.min_syllables,
        max_syllables=fam.max_syllables,
        onsets=", ".join(fam.onsets),
        vowels=", ".join(fam.vowels),
        codas=", ".join(fam.codas) or "none",
        harmony=harmony,
        n=n,
        context=context,
    )


@generators.register(
    "phonotactic_family",
    description="Validate candidate names against a phonotactic family inventory",
)
def phonotactic_family(*, names: Iterable[str], family="japanese_cv") -> Iterable[str]:
    """Yield the ``names`` that are legal in ``family``.

    Pair with ``phonotactic_prompt``: send the prompt to an LLM, parse its
    lines, and pass them here as ``names`` to drop anything off-family.

    >>> list(phonotactic_family(names=['kimono', 'strik', 'sakura'], family='japanese_cv'))
    ['kimono', 'sakura']
    """
    for name in names:
        name = name.strip().lower()
        if name and validate_phonotactic(name, family):
            yield name
