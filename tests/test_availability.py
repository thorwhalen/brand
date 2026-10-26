"""Offline tests for the availability, company and trademark scorers.

Network calls are replaced by fakes, so these pin the tri-state contract:
True = available, False = taken, None = the check could not answer.
"""

import pytest
import requests

import brand
from brand._scorers import availability, company


class _Resp:
    def __init__(self, status_code=200, payload=None, text="", url=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.url = url

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def _fake(monkeypatch, method, func):
    monkeypatch.setattr(requests, method, func)


@pytest.mark.parametrize("code,expected", [(404, True), (200, False), (429, None)])
def test_rdap_com(monkeypatch, code, expected):
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(code))
    assert brand.scorers["rdap_com"]("somename") is expected


def test_rdap_unsupported_tld_is_unknown():
    assert availability._rdap_is_available("somename.xyz") is None


@pytest.mark.parametrize("scorer", ["pypi", "npm", "npm_scope"])
@pytest.mark.parametrize("code,expected", [(404, True), (200, False), (403, None)])
def test_platform_scorers_tri_state(monkeypatch, scorer, code, expected):
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(code))
    assert brand.scorers[scorer]("SomeName") is expected


def test_platform_network_error_is_unknown(monkeypatch):
    def boom(url, **kw):
        raise requests.ConnectionError("down")

    _fake(monkeypatch, "get", boom)
    assert brand.scorers["npm"]("somename") is None


def test_npm_uses_registry_and_lowercase(monkeypatch):
    seen = []
    _fake(monkeypatch, "get", lambda url, **kw: seen.append(url) or _Resp(404))
    brand.scorers["npm"]("SomeName")
    assert seen == ["https://registry.npmjs.org/somename"]


def test_domain_sale_status(monkeypatch):
    page = (
        "<h1>thisname.com is for sale</h1> Fee $99. Buy now for $2,495 at Afternic."
        " Price: $2,495. Similar: $5,995"
    )
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(200, text=page, url=url))
    info = availability.domain_sale_status("thisname.com")
    assert info["for_sale"] is True
    assert info["price"] == "$2,495"
    assert "afternic" in info["markers"]


def test_normalize_entity_name():
    assert company.normalize_entity_name("Thoremin, Inc.") == "thoremin"
    assert company.normalize_entity_name("Lumex LLC") == "lumex"


def test_company_name_us_without_token_is_unknown(monkeypatch):
    monkeypatch.delenv("OPENCORPORATES_API_TOKEN", raising=False)
    assert brand.scorers["company_name_us"]("somename") is None


def test_company_us_states(monkeypatch):
    def get(url, params=None, **kw):
        if "ny.gov" in url:
            return _Resp(200, [{"current_entity_name": "SOMENAME LLC"}])
        return _Resp(200, [])

    _fake(monkeypatch, "get", get)
    matches = company.us_state_registry_matches("somename")
    assert matches["NY"] == ["SOMENAME LLC"] and matches["CO"] == []
    assert brand.scorers["company_us_states"]("somename") is False


def test_company_us_states_all_failing_is_unknown(monkeypatch):
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(500))
    assert brand.scorers["company_us_states"]("somename") is None


def test_company_us_sec(monkeypatch):
    hits = {"hits": {"hits": [{"_source": {"entity": "SOMENAME INC"}}]}}
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(200, hits))
    assert brand.scorers["company_us_sec"]("somename") is False
    assert brand.scorers["company_us_sec"]("othername") is True


def _tm_hit(wordmark, alive, classes):
    return {
        "source": {
            "wordmark": wordmark,
            "alive": alive,
            "internationalClass": [f"IC {c}" for c in classes],
        }
    }


def test_trademark_us_classes_and_liveness(monkeypatch):
    hits = [
        _tm_hit("SOMENAME", True, ["035"]),  # live, irrelevant class
        _tm_hit("SOMENAME", False, ["009"]),  # dead
        _tm_hit("SOMENAME PRO", True, ["009"]),  # not exact
    ]
    _fake(monkeypatch, "post", lambda url, **kw: _Resp(200, {"hits": {"hits": hits}}))
    assert brand.scorers["trademark_us"]("somename") is True
    assert brand.scorers["trademark_us"]("somename", classes=None) is False
    assert brand.scorers["trademark_us"]("somename", classes=("035",)) is False


def test_trademark_us_failure_is_unknown(monkeypatch):
    _fake(monkeypatch, "post", lambda url, **kw: _Resp(503))
    assert brand.scorers["trademark_us"]("somename") is None


def test_domain_sale_status_ignores_marketplace_names_in_code(monkeypatch):
    page = (
        "<script>var closedOn = 1; var usedOne = 2;</script><h1>Freehand drawing</h1>"
    )
    page = page.replace("closedOn", "losedo")  # a bare 'sedo' inside an identifier
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(200, text=page, url=url))
    assert availability.domain_sale_status("freehand.com")["for_sale"] is False
