"""Tests for retry on throttling, rate limiting and rescore_unknown."""

from unittest import mock

import brand
from brand import _http
from brand.pipeline import run_pipeline, rescore_unknown
from brand.registry import Registry


class _Resp:
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


def test_retry_then_success():
    seq = [_Resp(429, {"Retry-After": "0"}), _Resp(429), _Resp(200)]
    with mock.patch("requests.get", side_effect=seq), mock.patch("time.sleep"):
        r = _http.request_with_retry("GET", "http://x", backoff=0)
    assert r.status_code == 200


def test_retry_gives_up_and_returns_last_response():
    with (
        mock.patch("requests.get", return_value=_Resp(429)) as m,
        mock.patch("time.sleep"),
    ):
        r = _http.request_with_retry("GET", "http://x", max_retries=2, backoff=0)
    assert r.status_code == 429 and m.call_count == 3


def test_no_retry_on_other_codes():
    with mock.patch("requests.get", return_value=_Resp(404)) as m:
        _http.request_with_retry("GET", "http://x")
    assert m.call_count == 1


def test_rate_limiter_spaces_calls():
    lim = _http.RateLimiter(50)  # 20 ms apart
    sleeps = []
    with mock.patch("brand._http.time.sleep", sleeps.append):
        for _ in range(5):
            lim.wait()
    assert len(sleeps) == 4
    assert sleeps[-1] > 0.05  # the fifth call is scheduled ~80 ms out


def test_registry_carries_rate_limit():
    r = Registry("scorers")
    r.register("a", rate_limit=2, max_workers=3)(lambda n: 1)
    assert (r["a"].rate_limit, r["a"].max_workers) == (2, 3)
    assert brand.scorers["npm_scope"].rate_limit == 1


def test_rescore_unknown(tmp_path):
    calls = {"n": 0}

    @brand.scorers.register("_flaky_test", requires_network=True)
    def flaky(name):
        calls["n"] += 1
        return None if calls["n"] <= 2 else True

    from brand.stages import Score

    kw = dict(names=["a", "b"], project_name="p", pipeline_dir=str(tmp_path))
    run_pipeline([Score(["_flaky_test"])], **kw)
    assert rescore_unknown("p", "_flaky_test", pipeline_dir=str(tmp_path)) == 2
    import json

    final = json.load(open(tmp_path / "p" / "final" / "results.json"))
    assert all(c["scores"]["_flaky_test"] is True for c in final)
    brand.scorers.unregister("_flaky_test")
