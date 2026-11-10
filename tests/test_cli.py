"""Offline tests for ``python -m brand domains``: the check is injected, never the network."""

import json

from brand.__main__ import domains, main


def _check(taken):
    def check(domain):
        return {
            "domain": domain,
            "available": None if domain.endswith(".eu") else domain not in taken,
            "source": "rdap",
            "checked_utc": "2026-11-10T00:00:00Z",
        }

    return check


def test_domains_json_rows_and_exit_code(capsys):
    code = domains(["foo", "bar.eu", "--tlds", ".com,io", "--json"], check=_check({"foo.com"}))
    rows = json.loads(capsys.readouterr().out)
    assert [(r["domain"], r["verdict"]) for r in rows] == [
        ("foo.com", "taken"),
        ("foo.io", "free"),
        ("bar.eu", "unknown"),
    ]
    assert code == 0


def test_domains_exits_1_when_nothing_is_free(capsys):
    assert domains(["foo", "--tlds", "com"], check=_check({"foo.com"})) == 1
    out = capsys.readouterr().out
    assert out.splitlines()[0].split() == ["domain", "verdict", "source", "checked_utc"]
    assert "taken" in out


def test_unknown_command_is_usage_error(capsys):
    assert main(["nope"]) == 2
    assert "domains" in capsys.readouterr().err
