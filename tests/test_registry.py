"""Tests for duplicate-key handling in Registry."""

import warnings

import pytest

from brand.registry import Registry


def _f(n):
    return 1


def _g(n):
    return 2


def test_duplicate_warns_by_default_and_overwrites():
    r = Registry("scorers")
    r.register("x")(_f)
    with pytest.warns(UserWarning, match="already has 'x'"):
        r.register("x")(_g)
    assert r["x"].func is _g


def test_same_function_is_silent():
    r = Registry("scorers")
    r.register("x")(_f)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        r.register("x")(_f)


def test_raise_and_overwrite_modes():
    r = Registry("scorers", on_duplicate="raise")
    r.register("x")(_f)
    with pytest.raises(ValueError):
        r.register("x")(_g)
    assert r["x"].func is _f
    q = Registry("scorers", on_duplicate="overwrite")
    q.register("x")(_f)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        q.register("x")(_g)


def test_bare_decorator_and_bad_policy():
    r = Registry("scorers")
    r.register(_f)
    with pytest.warns(UserWarning):
        r.register(_f.__class__(_g.__code__, globals(), "_f"))
    with pytest.raises(ValueError):
        Registry("x", on_duplicate="nope")
