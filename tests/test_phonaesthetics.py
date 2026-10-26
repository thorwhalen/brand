"""Tests for the phonaesthetics scorer."""

import brand


def test_components_and_score():
    r = brand.scorers["phonaesthetics"]("lumeni")
    assert r["sonority"] == 1.0 and r["reduplication"] is False
    assert 0 < r["score"] < 1.5


def test_reduplication_penalised_and_weights_override():
    f = brand.scorers["phonaesthetics"]
    assert f("lalamo")["reduplication"] is True
    zero = f("lalamo", weights={k: 0 for k in f.func.__globals__["DEFAULT_PHONAESTHETIC_WEIGHTS"]})
    assert zero["score"] == 0


def test_english_word_flag():
    assert brand.scorers["phonaesthetics"]("house")["english_word"] is True
