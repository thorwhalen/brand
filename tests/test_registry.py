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
    assert r["_f"].func is _f
    with pytest.raises(ValueError):
        Registry("x", on_duplicate="nope")


def test_warning_points_at_caller_and_callable_objects_warn():
    class C:
        def __call__(self, n):
            return 0

        def __repr__(self):
            return "C()"

    r = Registry("scorers")
    r.register("c")(C())
    with pytest.warns(UserWarning) as w:
        r.register("c")(C())
    assert w[0].filename == __file__


def test_bare_register_warning_points_at_caller():
    r = Registry("scorers")
    r.register(_f)
    other = type(_f)(_g.__code__, globals(), "_f")
    with pytest.warns(UserWarning) as w:
        r.register(other)
    assert w[0].filename == __file__


def test_on_duplicate_is_assignable_and_validated():
    r = Registry("scorers")
    assert r.on_duplicate == "warn"
    r.on_duplicate = "raise"
    r.register("x")(_f)
    with pytest.raises(ValueError):
        r.register("x")(_g)
    with pytest.raises(ValueError):
        r.on_duplicate = "nope"
    assert r.on_duplicate == "raise"


def test_unregister_removes_and_returns():
    r = Registry("scorers")
    r.register("x")(_f)
    assert r.unregister("x").func is _f and "x" not in r
    r.register("x")(_g)  # the name is free again: no duplicate warning
    with pytest.raises(KeyError, match="no 'y'"):
        r.unregister("y")
