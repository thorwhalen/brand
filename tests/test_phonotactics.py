"""Tests for the phonotactic_family generator, prompt and validator."""

import pytest

import brand
from brand._phonotactics import (
    PHONOTACTIC_FAMILIES,
    PhonotacticFamily,
    phonotactic_prompt,
    validate_phonotactic,
)


def test_generator_filters_off_family_names():
    gen = brand.generators["phonotactic_family"]
    out = list(gen(names=["Kimono", "strik", "sakura", ""], family="japanese_cv"))
    assert out == ["kimono", "sakura"]


def test_bantu_is_open_syllables_only():
    assert validate_phonotactic("mbalo", "bantu_prenasalised")
    assert not validate_phonotactic("balot", "bantu_prenasalised")


def test_finnic_vowel_harmony():
    assert validate_phonotactic("kelito", "finnic_harmony")  # neutral e,i + back o
    assert validate_phonotactic("tolyva", "finnic_harmony") is False
    assert validate_phonotactic("mytyle", "finnic_harmony")


def test_prompt_mentions_inventory_and_context():
    p = phonotactic_prompt("finnic_harmony", context="a tea shop", n=7)
    assert (
        "a tea shop" in p
        and "Compose 7" in p
        and "k, l, m" in p
        and "harmony" in p.lower()
    )


def test_unknown_family_raises():
    with pytest.raises(KeyError):
        validate_phonotactic("kimono", "nope")


def test_validator_edge_cases():
    assert not validate_phonotactic("kimono\n", "japanese_cv")
    assert validate_phonotactic("kälö", "finnic_harmony")
    assert validate_phonotactic("KIMONO", "japanese_cv")


def test_custom_family_validation_and_harmony_only_on_vowels():
    from brand._phonotactics import PhonotacticFamily

    fam = PhonotacticFamily(
        onsets=tuple("kyt"), vowels=tuple("aouä"), harmony=("aou", "yä")
    )
    assert validate_phonotactic("yaka", fam)
    with pytest.raises(ValueError):
        PhonotacticFamily(onsets=(), vowels=())
    with pytest.raises(ValueError):
        PhonotacticFamily(onsets=(), vowels=("a",), min_syllables=5, max_syllables=2)


def test_generator_rejects_bare_string():
    with pytest.raises(TypeError):
        list(brand.generators["phonotactic_family"](names="kimono"))


def test_japanese_illegal_syllables():
    for bad in ("tita", "hufu", "wuwo", "fafa"):
        assert not validate_phonotactic(bad, "japanese_cv"), bad
    for good in ("chitsu", "kinshi", "fuji", "sakura"):
        assert validate_phonotactic(good, "japanese_cv"), good


def test_register_family_and_scorer():
    from brand._phonotactics import PhonotacticFamily, register_family

    register_family("ab", PhonotacticFamily(onsets=("b",), vowels=("a",)))
    try:
        assert validate_phonotactic("baba", "ab")
        assert brand.scorers["in_phonotactic_family"]("baba", family="ab") is True
        assert brand.scorers["in_phonotactic_family"]("kimono", family="ab") is False
    finally:
        from brand._phonotactics import PHONOTACTIC_FAMILIES

        del PHONOTACTIC_FAMILIES["ab"]


def test_phonotactic_ai_with_injected_ask():
    seen = []

    def ask(prompt):
        seen.append(prompt)
        return "kimono\nstrik\n\nSakura\nkimono\n"

    out = brand.generators["phonotactic_ai"](context="tea", ask=ask)
    assert out == ["kimono", "sakura"] and "tea" in seen[0] and "japanese_cv" in seen[0]


def test_enumerate_yields_only_valid_unique_names():
    from brand._phonotactics import phonotactic_enumerate

    out = list(
        phonotactic_enumerate(family="bantu_prenasalised", syllables=2, limit=500)
    )
    assert len(out) == 500 and len(set(out)) == 500
    assert all(validate_phonotactic(n, "bantu_prenasalised") for n in out)
    assert (
        len(list(phonotactic_enumerate(family="japanese_cv", syllables=2, limit=1000)))
        == 1000
    )


def test_enumerate_rejects_out_of_range_syllables():
    from brand._phonotactics import phonotactic_enumerate

    with pytest.raises(ValueError):
        phonotactic_enumerate(family="japanese_cv", syllables=9)


def test_enumerate_is_lazy_and_deduplicated():
    import time

    from brand._phonotactics import phonotactic_enumerate

    t0 = time.time()
    assert (
        len(list(phonotactic_enumerate(family="japanese_cv", syllables=4, limit=10)))
        == 10
    )
    assert time.time() - t0 < 2
    out = list(phonotactic_enumerate(family="finnic_harmony", syllables=2, limit=3000))
    assert len(out) == len(set(out)) == 3000
    with pytest.raises(ValueError):
        phonotactic_enumerate(limit=-1)


def _brute_force(family, syllables):
    """Every legal name, found the slow way: build all, then validate."""
    import itertools

    fam = PHONOTACTIC_FAMILIES[family]
    parts = [o + v + c for o in ("",) + fam.onsets for v in fam.vowels for c in ("",) + fam.codas]
    return {
        n
        for n in map("".join, itertools.product(parts, repeat=syllables))
        if validate_phonotactic(n, family)
    }


@pytest.mark.parametrize("family", sorted(PHONOTACTIC_FAMILIES))
def test_enumerate_finds_exactly_the_legal_names(family):
    from brand._phonotactics import phonotactic_enumerate

    out = list(phonotactic_enumerate(family=family, syllables=2, limit=None))
    assert len(out) == len(set(out))
    assert set(out) == _brute_force(family, 2)


def test_enumerate_small_limit_is_not_all_onsetless():
    from brand._phonotactics import phonotactic_enumerate

    first = list(phonotactic_enumerate(family="japanese_cv", syllables=2, limit=5))
    assert not any(n[0] in "aeiou" for n in first)


def test_enumerate_seed_is_reproducible_varied_and_valid():
    from brand._phonotactics import phonotactic_enumerate

    run = lambda seed: list(
        phonotactic_enumerate(family="finnic_harmony", syllables=3, limit=200, seed=seed)
    )
    a = run(1)
    assert a == run(1) and a != run(2)
    assert len(set(a)) == 200 and all(validate_phonotactic(n, "finnic_harmony") for n in a)
    assert len({n[0] for n in a}) > 3  # spread over first syllables, not lopsided


def test_enumerate_seed_needs_a_limit_and_stops_when_exhausted():
    from brand._phonotactics import phonotactic_enumerate

    with pytest.raises(ValueError, match="needs a limit"):
        phonotactic_enumerate(seed=0, limit=None)
    tiny = PhonotacticFamily(onsets=("k", "t"), vowels=("a", "i"), min_syllables=1)
    out = list(phonotactic_enumerate(family=tiny, syllables=1, limit=100, seed=0))
    assert sorted(out) == ["a", "i", "ka", "ki", "ta", "ti"]  # stopped by MAX_SAMPLE_STALLS


def test_enumerate_never_yields_what_the_validator_rejects():
    from brand._phonotactics import phonotactic_enumerate

    # "kai" is illegal but is built as "ka"+"i": a ban that spans two syllables
    odd = PhonotacticFamily(
        onsets=("k",), vowels=("a", "i", "ai"), illegal_syllables=("kai",), min_syllables=1
    )
    for kw in ({}, {"seed": 0}):
        out = list(phonotactic_enumerate(family=odd, syllables=2, limit=500, **kw))
        assert out and all(validate_phonotactic(n, odd) for n in out)


def test_enumerate_of_a_family_with_no_legal_syllable_is_empty():
    from brand._phonotactics import phonotactic_enumerate

    dead = PhonotacticFamily(onsets=("k",), vowels=("a",), illegal_syllables=("k", "a"), min_syllables=1)
    assert list(phonotactic_enumerate(family=dead, syllables=1)) == []
    assert list(phonotactic_enumerate(family=dead, syllables=1, limit=3, seed=0)) == []
