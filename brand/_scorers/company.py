"""Company name and trademark scorers (United States).

Checks whether a candidate name is already used by a US business entity or a
live US trademark.  Sources, all free and keyless unless noted:

- **State business registries** published as open data (Socrata): New York,
  Colorado, Oregon, Connecticut.  These include *foreign* entities, i.e.
  companies formed elsewhere (very often Delaware) that registered to do
  business in the state.  See ``STATE_REGISTRIES``; add a state by adding a row.
- **SEC EDGAR** entity names: every company that filed with the SEC (including
  Form D filings by venture-funded startups).
- **OpenCorporates**: all US jurisdictions, but its API needs a token
  (``OPENCORPORATES_API_TOKEN`` env var).  Without one the check is unknown.
- **USPTO trademarks** via the search backend of tmsearch.uspto.gov.

Delaware's and California's own registries have no open API (Delaware's search
is CAPTCHA-gated, California's sits behind a bot wall), so they are covered only
indirectly, through the sources above.

Scorers return ``True`` (no conflict found), ``False`` (conflict) or ``None``
(the check could not run).  ``None`` is never "available".
"""

import os
import re

import requests

from brand.registry import scorers

_CORP_SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|company"
    r"|lp|llp|pllc|pc|plc|the)\b\.?"
)


def normalize_entity_name(s: str) -> str:
    """Lowercase, drop corporate suffixes and everything but letters and digits.

    >>> normalize_entity_name("Thoremin, Inc.")
    'thoremin'
    >>> normalize_entity_name("THE LUMEX COMPANY LLC")
    'lumex'
    """
    s = _CORP_SUFFIXES.sub("", s.lower().strip())
    return re.sub(r"[^a-z0-9]", "", s)


def _exact_matches(name: str, entity_names) -> list[str]:
    target = normalize_entity_name(name)
    return [n for n in entity_names if target and normalize_entity_name(n) == target]


# ---------------------------------------------------------------------------
# State registries (Socrata open data)
# ---------------------------------------------------------------------------

# state -> (dataset url, name field, what the dataset covers)
STATE_REGISTRIES = {
    "NY": (
        "https://data.ny.gov/resource/n9v6-gdp6.json",
        "current_entity_name",
        "active corporations and LLCs, domestic and foreign",
    ),
    "CO": (
        "https://data.colorado.gov/resource/4ykn-tg5h.json",
        "entityname",
        "all business entities, any status",
    ),
    "OR": (
        "https://data.oregon.gov/resource/tckn-sxa6.json",
        "business_name",
        "active businesses, domestic and foreign",
    ),
    "CT": (
        "https://data.ct.gov/resource/n7gp-d28j.json",
        "name",
        "all business entities, any status",
    ),
}


def _socrata_prefix_search(url: str, field: str, name: str, *, timeout=20, limit=50):
    """Entity names in a Socrata dataset that start with *name* (case-insensitive)."""
    word = re.sub(r"[^A-Za-z0-9]", "", name).upper()
    r = requests.get(
        url,
        params={
            "$select": field,
            "$where": f"upper({field}) like '{word}%'",
            "$limit": limit,
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return [row.get(field, "") for row in r.json()]


def us_state_registry_matches(name: str, *, registries=None) -> dict:
    """Per state: the exact-match entity names found, or None if the query failed."""
    registries = STATE_REGISTRIES if registries is None else registries
    out = {}
    for state, (url, field, _) in registries.items():
        try:
            out[state] = _exact_matches(name, _socrata_prefix_search(url, field, name))
        except (requests.RequestException, ValueError):
            out[state] = None
    return out


@scorers.register(
    "company_us_states",
    description="No US entity with this name in state open-data registries (NY, CO, OR, CT)",
    cost="moderate",
    requires_network=True,
    latency="medium",
    parallelizable=True,
)
def company_us_states(name: str) -> bool | None:
    """True if no state registry in ``STATE_REGISTRIES`` has this exact name.

    None if every registry query failed.
    """
    results = us_state_registry_matches(name)
    if any(results.values()):
        return False
    if all(v is None for v in results.values()):
        return None
    return True


# ---------------------------------------------------------------------------
# SEC EDGAR entities
# ---------------------------------------------------------------------------

# SEC asks for "<name> <email>" and refuses URL-style agents; override via env.
EDGAR_USER_AGENT = os.environ.get(
    "SEC_EDGAR_USER_AGENT", "brand-name-checker brand-checker@example.org"
)


def sec_edgar_matches(name: str, *, timeout=15) -> list[str]:
    """SEC EDGAR entity names that equal *name* once normalized."""
    r = requests.get(
        "https://efts.sec.gov/LATEST/search-index",
        params={"keysTyped": name},
        headers={"User-Agent": EDGAR_USER_AGENT},
        timeout=timeout,
    )
    r.raise_for_status()
    hits = r.json().get("hits", {}).get("hits", [])
    return _exact_matches(name, [h["_source"].get("entity", "") for h in hits])


@scorers.register(
    "company_us_sec",
    description="No SEC EDGAR filer with this name",
    cost="cheap",
    requires_network=True,
    latency="fast",
    parallelizable=True,
)
def company_us_sec(name: str) -> bool | None:
    """True if no SEC filer has this exact name, None if EDGAR could not be reached."""
    try:
        return not sec_edgar_matches(name)
    except (requests.RequestException, ValueError, KeyError):
        return None


# ---------------------------------------------------------------------------
# OpenCorporates (all US jurisdictions; needs a token)
# ---------------------------------------------------------------------------


def _opencorporates_search(
    name: str, *, jurisdiction="us", api_token=None
) -> list[dict]:
    """Search OpenCorporates for companies matching *name*.

    Raises ``requests.HTTPError`` on failure (e.g. 401 without a token).
    """
    params = {"q": name, "jurisdiction_code": jurisdiction, "per_page": 30}
    if api_token:
        params["api_token"] = api_token
    r = requests.get(
        "https://api.opencorporates.com/v0.4/companies/search",
        params=params,
        timeout=15,
    )
    r.raise_for_status()
    companies = r.json().get("results", {}).get("companies", [])
    return [c.get("company", {}) for c in companies]


@scorers.register(
    "company_name_us",
    description="US company name availability via OpenCorporates (needs OPENCORPORATES_API_TOKEN)",
    cost="moderate",
    requires_network=True,
    latency="medium",
    parallelizable=True,
)
def company_name_available_us(name: str, *, api_token=None) -> bool | None:
    """True if OpenCorporates has no US company with this exact name.

    None when there is no API token or the query failed: an unanswered
    check is not an available name.
    """
    api_token = api_token or os.environ.get("OPENCORPORATES_API_TOKEN")
    if not api_token:
        return None
    try:
        companies = _opencorporates_search(name, api_token=api_token)
    except (requests.RequestException, ValueError):
        return None
    return not _exact_matches(name, [c.get("name", "") for c in companies])


# ---------------------------------------------------------------------------
# USPTO trademarks
# ---------------------------------------------------------------------------

USPTO_SEARCH_URL = "https://tmsearch.uspto.gov/prod-stage-v1-0-0/tmsearch"

# Nice classes most relevant to software and consumer products; override per call.
DEFAULT_TRADEMARK_CLASSES = ("009", "015", "041", "042")


def uspto_trademarks(name: str, *, size=100, timeout=20) -> list[dict]:
    """Trademarks whose word mark contains *name* as a word, live or dead.

    Each record: ``wordmark``, ``alive``, ``classes`` (e.g. ``['009']``),
    ``status``, ``owner``, ``serial``, ``registration``.
    """
    r = requests.post(
        USPTO_SEARCH_URL,
        json={
            "query": {"bool": {"must": [{"match_phrase": {"WM": name}}]}},
            "size": size,
            "_source": [
                "wordmark",
                "alive",
                "internationalClass",
                "statusDescription",
                "ownerName",
                "id",
                "registrationId",
            ],
        },
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
        timeout=timeout,
    )
    r.raise_for_status()
    out = []
    for h in r.json()["hits"]["hits"]:
        s = h["source"]
        out.append(
            {
                "wordmark": s.get("wordmark") or "",
                "alive": bool(s.get("alive")),
                "classes": [
                    c.replace("IC", "").strip()
                    for c in s.get("internationalClass") or []
                ],
                "status": s.get("statusDescription"),
                "owner": (s.get("ownerName") or [None])[0],
                "serial": s.get("id"),
                "registration": s.get("registrationId"),
            }
        )
    return out


def trademark_conflicts_us(
    name: str, *, classes=DEFAULT_TRADEMARK_CLASSES
) -> list[dict]:
    """Live marks whose word mark equals *name* (normalized), in *classes*.

    ``classes=None`` means any class.
    """
    target = normalize_entity_name(name)
    return [
        t
        for t in uspto_trademarks(name)
        if t["alive"]
        and normalize_entity_name(t["wordmark"]) == target
        and (classes is None or set(t["classes"]) & set(classes))
    ]


@scorers.register(
    "trademark_us",
    description="No live exact USPTO word mark in classes 9/15/41/42",
    cost="moderate",
    requires_network=True,
    latency="medium",
    parallelizable=True,
)
def trademark_check_us(name: str, *, classes=DEFAULT_TRADEMARK_CLASSES) -> bool | None:
    """True if no live exact word mark exists in *classes*, None if USPTO failed.

    Exact word marks only; a clearance search also weighs phonetic and visual
    equivalents (``uspto_trademarks`` returns the wider set to look at).
    """
    try:
        return not trademark_conflicts_us(name, classes=classes)
    except (requests.RequestException, ValueError, KeyError):
        return None
