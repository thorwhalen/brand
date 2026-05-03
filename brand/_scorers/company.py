"""Company name availability scorers.

Checks whether a candidate name is available for US company registration
by querying OpenCorporates and the USPTO trademark database.
"""

import requests

from brand.registry import scorers


# ---------------------------------------------------------------------------
# OpenCorporates (company registry)
# ---------------------------------------------------------------------------


def _opencorporates_search(name: str, *, jurisdiction="us") -> list[dict]:
    """Search OpenCorporates for companies matching *name*.

    Returns a list of matching company dicts (empty = no matches found).
    Uses the free API tier (no key required, rate-limited).
    """
    try:
        r = requests.get(
            "https://api.opencorporates.com/v0.4/companies/search",
            params={
                "q": name,
                "jurisdiction_code": jurisdiction,
                "per_page": 10,
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        companies = data.get("results", {}).get("companies", [])
        return [c.get("company", {}) for c in companies]
    except requests.RequestException:
        return []


def _is_exact_or_close_match(name: str, companies: list[dict]) -> bool:
    """Check if any returned company is an exact or near-exact match.

    Compares normalized names (lowercase, stripped of common suffixes like
    LLC, Inc, Corp, etc.).
    """
    import re

    def _normalize(s):
        s = s.lower().strip()
        # Remove common corporate suffixes
        s = re.sub(
            r"\b(inc|incorporated|llc|ltd|limited|corp|corporation|co|company"
            r"|lp|llp|pllc|pc|plc)\b\.?",
            "",
            s,
        )
        # Remove punctuation and extra whitespace
        s = re.sub(r"[^a-z0-9]", "", s)
        return s

    target = _normalize(name)
    if not target:
        return False

    for company in companies:
        company_name = company.get("name", "")
        if _normalize(company_name) == target:
            return True
    return False


@scorers.register(
    "company_name_us",
    description="US company name availability via OpenCorporates",
    cost="moderate",
    requires_network=True,
    latency="medium",
    parallelizable=True,
)
def company_name_available_us(name: str) -> bool:
    """Check if *name* is available as a US company name.

    Searches OpenCorporates for exact/near matches. Returns True if no
    conflicting company was found. Note: this is an approximation —
    official state-level checks are authoritative.

    >>> isinstance(company_name_available_us('xyzqwk'), bool)
    True
    """
    companies = _opencorporates_search(name, jurisdiction="us")
    return not _is_exact_or_close_match(name, companies)


# ---------------------------------------------------------------------------
# USPTO Trademark (TESS-like search via public API)
# ---------------------------------------------------------------------------


@scorers.register(
    "trademark_us",
    description="US trademark conflict check via USPTO",
    cost="moderate",
    requires_network=True,
    latency="medium",
    parallelizable=True,
)
def trademark_check_us(name: str) -> bool:
    """Check if *name* conflicts with a registered US trademark.

    Uses the USPTO's public Trademark Status and Document Retrieval (TSDR)
    API. Returns True if no live trademark conflict was found.

    Note: this searches for exact word marks only. A full clearance search
    should include phonetic equivalents (done by trademark attorneys).

    >>> isinstance(trademark_check_us('xyzqwk'), bool)
    True
    """
    try:
        r = requests.get(
            "https://tsdr.uspto.gov/documentexternal/statuskeynew",
            params={"sn": "", "rn": "", "td": name},
            timeout=15,
            headers={"Accept": "application/json"},
        )
        # If we get a 404 or empty result, no trademark found
        if r.status_code == 404:
            return True
        if r.status_code != 200:
            return True  # Can't determine, optimistically assume available

        data = r.json()
        # If no trademark document found, name is clear
        if not data or data.get("error"):
            return True
        return False
    except (requests.RequestException, ValueError):
        # Network error or JSON parse error — can't determine
        return True  # Optimistic default; pipeline should re-check later
