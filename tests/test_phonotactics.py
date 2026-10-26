"""Tests for the phonotactic_family generator, prompt and validator."""

import pytest

import brand
from brand._phonotactics import phonotactic_prompt, validate_phonotactic


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
    assert "a tea shop" in p and "7" in p and "harmony" in p.lower()


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
        onsets=tuple("kyt"), vowels=tuple("aouä"), harmony=("aou", "ä")
    )
    assert validate_phonotactic("yaka", fam)
    with pytest.raises(ValueError):
        PhonotacticFamily(onsets=(), vowels=())
    with pytest.raises(ValueError):
        PhonotacticFamily(onsets=(), vowels=("a",), min_syllables=5, max_syllables=2)


def test_generator_rejects_bare_string():
    with pytest.raises(TypeError):
        list(brand.generators["phonotactic_family"](names="kimono"))
