"""Availability scorers: DNS, WHOIS, domain, platform handles.

These scorers check whether a candidate name is available on various
platforms.  They return ``True`` (available), ``False`` (taken) or ``None``
(unknown: the check could not run or its answer was ambiguous).  ``None`` is
never "available": a ``Filter(rules={"dns_com": True})`` drops it.

All network scorers are tagged with ``requires_network=True`` and appropriate
cost/latency metadata so the pipeline engine can schedule them efficiently.
"""

import socket

import requests

from brand._http import request_with_retry
from brand.registry import scorers


# ---------------------------------------------------------------------------
# DNS / WHOIS helpers (adapted from brand.base)
# ---------------------------------------------------------------------------


def _dns_is_available(domain: str, *, timeout: int = 3) -> bool:
    """Fast DNS-only check.  Returns True if domain does NOT resolve."""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(domain)
        return False
    except (socket.gaierror, socket.timeout, OSError):
        return True
    finally:
        socket.setdefaulttimeout(old_timeout)


def _whois_is_available(domain: str) -> bool | None:
    """WHOIS-based check.  True if unregistered, None if WHOIS failed."""
    try:
        import whois

        w = whois.whois(domain)
        if w.domain_name:
            return False
        return True
    except Exception as e:
        # python-whois raises on "No match", which means available
        if "no match" in str(e).lower():
            return True
        return None


# Authoritative registry RDAP servers (404 = not registered).  Extend to add TLDs.
RDAP_SERVERS = {
    ".com": "https://rdap.verisign.com/com/v1/domain/",
    ".net": "https://rdap.verisign.com/net/v1/domain/",
}


def _rdap_is_available(domain: str, *, timeout: int = 10) -> bool | None:
    """Registry RDAP check.  True if not registered, None if unsupported/failed."""
    tld = "." + domain.rsplit(".", 1)[-1]
    base = RDAP_SERVERS.get(tld)
    if base is None:
        return None
    try:
        r = request_with_retry("GET", base + domain, timeout=timeout)
    except requests.RequestException:
        return None
    return {404: True, 200: False}.get(r.status_code)


def _url_is_available(
    url: str, *, available_codes=(404, 410), taken_codes=(200, 301)
) -> bool | None:
    """Check URL status code.  True if the resource doesn't exist, None if unclear."""
    try:
        r = request_with_retry("GET", url, timeout=10, allow_redirects=True)
    except requests.RequestException:
        return None
    if r.status_code in available_codes:
        return True
    if r.status_code in taken_codes:
        return False
    return None  # e.g. 403 from a bot wall, 429, 5xx


# ---------------------------------------------------------------------------
# Domain scorers
# ---------------------------------------------------------------------------


def _make_domain_scorer(tld: str, scorer_name: str):
    """Factory for DNS+WHOIS two-pass domain availability scorers."""

    def domain_scorer(name: str) -> bool | None:
        domain = f"{name}{tld}"
        if not _dns_is_available(domain):
            return False
        rdap = _rdap_is_available(domain)
        return rdap if rdap is not None else _whois_is_available(domain)

    domain_scorer.__name__ = scorer_name
    domain_scorer.__doc__ = (
        f"Check if {{name}}{tld} is available (DNS, then registry RDAP or WHOIS)."
    )
    return domain_scorer


# Register domain scorers for common TLDs
_TLDS = {
    "dns_com": ".com",
    "dns_net": ".net",
    "dns_org": ".org",
    "dns_io": ".io",
    "dns_ai": ".ai",
    "dns_co": ".co",
    "dns_dev": ".dev",
    "dns_app": ".app",
}

for _name, _tld in _TLDS.items():
    _func = _make_domain_scorer(_tld, _name)
    # Quick DNS-only scorers
    scorers.register(
        _name,
        cost="cheap",
        requires_network=True,
        latency="fast",
        parallelizable=True,
        description=f"Domain availability for {_tld} (DNS + WHOIS)",
    )(_func)


# WHOIS-only scorer (slower but more reliable)
@scorers.register(
    "whois_com",
    cost="expensive",
    requires_network=True,
    latency="slow",
    parallelizable=True,
    description="WHOIS verification for .com domain",
)
def whois_com(name: str) -> bool | None:
    """Verify .com availability via WHOIS (slower, more reliable than DNS)."""
    return _whois_is_available(f"{name}.com")


@scorers.register(
    "rdap_com",
    cost="cheap",
    requires_network=True,
    latency="fast",
    parallelizable=True,
    rate_limit=5,
    description="Authoritative .com registration check via Verisign RDAP",
)
def rdap_com(name: str) -> bool | None:
    """True if ``{name}.com`` is not registered, per the .com registry's RDAP.

    Unlike DNS, this sees registered domains that have no DNS records.
    """
    return _rdap_is_available(f"{name}.com")


# Markers of a parked or for-sale landing page.  Extend as marketplaces appear.
FOR_SALE_MARKERS = (
    "is for sale",
    "buy this domain",
    "make an offer",
    "domain may be for sale",
    "afternic",
    "dan.com",
    "sedo.com",
    "sedoparking",
    "hugedomains",
    "atom.com",
    "squadhelp",
    "brandbucket",
    "spaceship.com",
    "parkingcrew",
    "bodis",
)


def _prices_by_frequency(html: str) -> list[str]:
    """Dollar amounts in *html*, most frequent first; ties go to the larger amount.

    >>> _prices_by_frequency("Fee $99. Buy for $2,395 or $2,395 now. Other: $5,995")
    ['$2,395', '$5,995', '$99']
    """
    import re
    from collections import Counter

    amounts = Counter(re.findall(r"\$\s?[0-9][0-9,]*(?:\.[0-9]{2})?", html))

    def value(a):
        return float(re.sub(r"[^0-9.]", "", a) or 0)

    ranked = sorted(amounts, key=lambda a: (-amounts[a], -value(a)))
    return [a.replace(" ", "") for a in ranked]


def domain_sale_status(domain: str, *, timeout: int = 10) -> dict:
    """Look at a registered domain's landing page for for-sale/parking markers.

    Returns ``{"reachable": bool, "final_url": str|None, "for_sale": bool|None,
    "markers": [...], "price": str|None, "prices": [...]}``.  On a page with
    for-sale markers, ``prices`` lists its ``$`` amounts, most repeated first,
    and ``price`` is the first of them.  Marketplace pages also show fees,
    lease terms and other listings, so ``price`` is a hint to confirm by eye,
    not a quote.
    """
    import re

    out = {
        "reachable": False,
        "final_url": None,
        "for_sale": None,
        "markers": [],
        "price": None,
        "prices": [],
    }
    for scheme in ("https://", "http://"):
        try:
            r = requests.get(
                scheme + domain,
                timeout=timeout,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
        except requests.RequestException:
            continue
        text = (r.url + " " + r.text[:200_000]).lower()
        out["reachable"] = True
        out["final_url"] = r.url
        out["markers"] = [m for m in FOR_SALE_MARKERS if m in text]
        out["for_sale"] = bool(out["markers"])
        if out["for_sale"]:
            out["prices"] = _prices_by_frequency(r.text)[:5]
            out["price"] = out["prices"][0] if out["prices"] else None
        return out
    return out


# ---------------------------------------------------------------------------
# Platform availability scorers
# ---------------------------------------------------------------------------


def _make_url_scorer(template: str, scorer_name: str, description: str):
    """Factory for URL-based availability scorers."""

    def url_scorer(name: str) -> bool | None:
        return _url_is_available(template.format(name.lower()))

    url_scorer.__name__ = scorer_name
    url_scorer.__doc__ = description
    return url_scorer


_PLATFORM_CHECKS = {
    "github_org": (
        "https://github.com/{}",
        "GitHub organization availability",
    ),
    "pypi": (
        "https://pypi.org/pypi/{}/json",
        "PyPI project name availability",
    ),
    # The registry, not www.npmjs.com, which answers bots with 403
    "npm": (
        "https://registry.npmjs.org/{}",
        "npm package name availability",
    ),
    # Lists a user's or org's packages; 404 when no such user or org exists
    "npm_scope": (
        "https://registry.npmjs.org/-/org/{}/package",
        "npm scope (@name, user or org) availability",
    ),
    "youtube": (
        "https://www.youtube.com/{}",
        "YouTube channel name availability",
    ),
}

# Requests per second; the registries below throttle (429) after a few dozen calls
_PLATFORM_RATE_LIMITS = {"npm": 1, "npm_scope": 1}

for _name, (_template, _desc) in _PLATFORM_CHECKS.items():
    _func = _make_url_scorer(_template, _name, _desc)
    scorers.register(
        _name,
        cost="moderate",
        requires_network=True,
        latency="medium",
        parallelizable=True,
        rate_limit=_PLATFORM_RATE_LIMITS.get(_name),
        description=_desc,
    )(_func)
