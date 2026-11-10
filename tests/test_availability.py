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


def test_rdap_unsupported_tld_is_unknown(monkeypatch):
    monkeypatch.setattr(availability, "rdap_bootstrap", lambda *a, **kw: {})
    assert availability._rdap_is_available("somename.xyz") is None


_BOOTSTRAP = {
    "services": [
        [["fr"], ["https://rdap.nic.fr/"]],
        [["app", "DEV"], ["http://plain.example/rdap", "https://pubapi.example/rdap/"]],
        [["com"], ["https://elsewhere.example/"]],
    ]
}


def test_rdap_bootstrap_maps_tlds_to_https_bases_and_caches(monkeypatch):
    monkeypatch.setattr(availability, "_rdap_bootstrap_cache", {})
    calls = []
    _fake(monkeypatch, "get", lambda url, **kw: calls.append(url) or _Resp(200, _BOOTSTRAP))
    table = availability.rdap_bootstrap()
    assert table[".fr"] == "https://rdap.nic.fr/domain/"
    assert table[".dev"] == table[".app"] == "https://pubapi.example/rdap/domain/"
    availability.rdap_bootstrap()
    assert calls == [availability.IANA_RDAP_BOOTSTRAP]  # fetched once


def test_rdap_bootstrap_failure_is_empty_and_asked_once(monkeypatch):
    monkeypatch.setattr(availability, "_rdap_bootstrap_cache", {})
    calls = []
    _fake(monkeypatch, "get", lambda url, **kw: calls.append(url) or _Resp(404))
    assert availability.rdap_bootstrap() == {}
    assert availability.rdap_bootstrap() == {} and len(calls) == 1


@pytest.mark.parametrize(
    "payload", [{"nope": []}, {"services": [[["fr"]]]}, {"services": "x"}, None]
)
def test_rdap_bootstrap_malformed_file_is_empty(monkeypatch, payload):
    monkeypatch.setattr(availability, "_rdap_bootstrap_cache", {})
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(200, payload))
    assert availability.rdap_bootstrap() == {}


def test_rdap_bootstrap_skips_entries_without_servers(monkeypatch):
    monkeypatch.setattr(availability, "_rdap_bootstrap_cache", {})
    payload = {"services": [[["xx"], []], *_BOOTSTRAP["services"]]}
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(200, payload))
    table = availability.rdap_bootstrap()
    assert ".xx" not in table and ".fr" in table


def test_rdap_server_prefers_the_local_table(monkeypatch):
    monkeypatch.setattr(availability, "_rdap_bootstrap_cache", {})
    _fake(monkeypatch, "get", lambda url, **kw: _Resp(200, _BOOTSTRAP))
    assert availability.rdap_server(".com") == availability.RDAP_SERVERS[".com"]
    assert availability.rdap_server(".FR") == "https://rdap.nic.fr/domain/"
    assert availability.rdap_server(".nope") is None


def _fake_whois(monkeypatch, behaviour):
    """Install a stand-in ``whois`` module whose ``whois()`` does *behaviour*."""
    import types

    mod = types.ModuleType("whois")
    mod.whois = lambda domain, **kw: behaviour(domain)
    monkeypatch.setitem(__import__("sys").modules, "whois", mod)


class WhoisDomainNotFoundError(Exception):  # the name python-whois raises
    pass


class WhoisQuotaExceededError(Exception):
    pass


def _raise(exc):
    def f(domain):
        raise exc

    return f


@pytest.mark.parametrize(
    "behaviour,expected",
    [
        (_raise(WhoisDomainNotFoundError("Domain not found.")), True),
        (_raise(Exception("No match for X.COM")), True),
        (_raise(WhoisQuotaExceededError("limit exceeded")), None),
        (lambda d: type("W", (), {"domain_name": d})(), False),
        (lambda d: type("W", (), {"domain_name": None})(), None),  # empty, not free
    ],
)
def test_whois_only_an_explicit_not_found_is_available(monkeypatch, behaviour, expected):
    _fake_whois(monkeypatch, behaviour)
    assert availability._whois_is_available("x.io") is expected


_UNCALLED = "uncalled"  # a pass that must not run


@pytest.mark.parametrize(
    "dns_free,rdap,whois,confirm,expected",
    [
        (False, _UNCALLED, _UNCALLED, True, (False, "dns")),  # resolves: taken
        (True, False, _UNCALLED, True, (False, "rdap")),
        (True, True, None, True, (True, "rdap+whois")),  # WHOIS unclear: RDAP stands
        (True, True, True, True, (True, "rdap+whois")),
        (True, True, False, True, (False, "rdap+whois")),  # WHOIS shows a record
        (True, True, _UNCALLED, False, (True, "rdap")),
        (True, None, True, True, (True, "whois")),  # no RDAP for the TLD
        (True, None, None, True, (None, None)),
    ],
)
def test_check_domain_passes(monkeypatch, dns_free, rdap, whois, confirm, expected):
    def answer(value):
        def check(domain):
            assert value is not _UNCALLED, "this pass should not have run"
            return value

        return check

    monkeypatch.setattr(availability, "_dns_is_available", lambda d: dns_free)
    monkeypatch.setattr(availability, "_rdap_is_available", answer(rdap))
    monkeypatch.setattr(availability, "_whois_is_available", answer(whois))
    r = availability.check_domain("name.music", confirm_with_whois=confirm)
    assert (r["available"], r["source"]) == expected
    assert r["domain"] == "name.music"
    assert __import__("re").fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", r["checked_utc"])


def test_domain_scorers_use_check_domain(monkeypatch):
    seen = []
    monkeypatch.setattr(
        availability,
        "check_domain",
        lambda d, **kw: seen.append((d, kw)) or {"available": True},
    )
    assert brand.scorers["dns_app"]("somename") is True
    assert seen == [("somename.app", {"confirm_with_whois": False})]


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
