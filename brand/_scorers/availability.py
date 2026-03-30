"""Availability scorers: DNS, WHOIS, domain, platform handles.

These scorers check whether a candidate name is available on various
platforms.  They return ``True`` (available) or ``False`` (taken).

All network scorers are tagged with ``requires_network=True`` and appropriate
cost/latency metadata so the pipeline engine can schedule them efficiently.
"""

import socket

import requests

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


def _whois_is_available(domain: str) -> bool:
    """WHOIS-based check.  Returns True if domain appears unregistered."""
    try:
        import whois

        w = whois.whois(domain)
        if w.domain_name:
            return False
        return True
    except Exception:
        return True


def _url_is_available(
    url: str, *, available_codes=(404, 410), taken_codes=(200, 301)
) -> bool:
    """Check URL status code.  Returns True if the resource doesn't exist."""
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        if r.status_code in available_codes:
            return True
        if r.status_code in taken_codes:
            return False
        # Ambiguous — default to "taken" to be conservative
        return False
    except requests.RequestException:
        # Network error — can't determine, assume taken
        return False


# ---------------------------------------------------------------------------
# Domain scorers
# ---------------------------------------------------------------------------


def _make_domain_scorer(tld: str, scorer_name: str):
    """Factory for DNS+WHOIS two-pass domain availability scorers."""

    def domain_scorer(name: str) -> bool:
        domain = f"{name}{tld}"
        if not _dns_is_available(domain):
            return False
        return _whois_is_available(domain)

    domain_scorer.__name__ = scorer_name
    domain_scorer.__doc__ = f"Check if {{name}}{tld} is available (DNS + WHOIS)."
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
def whois_com(name: str) -> bool:
    """Verify .com availability via WHOIS (slower, more reliable than DNS)."""
    return _whois_is_available(f"{name}.com")


# ---------------------------------------------------------------------------
# Platform availability scorers
# ---------------------------------------------------------------------------


def _make_url_scorer(template: str, scorer_name: str, description: str):
    """Factory for URL-based availability scorers."""

    def url_scorer(name: str) -> bool:
        return _url_is_available(template.format(name))

    url_scorer.__name__ = scorer_name
    url_scorer.__doc__ = description
    return url_scorer


_PLATFORM_CHECKS = {
    "github_org": (
        "https://github.com/{}",
        "GitHub organization availability",
    ),
    "pypi": (
        "https://pypi.org/project/{}/",
        "PyPI project name availability",
    ),
    "npm": (
        "https://www.npmjs.com/package/{}",
        "npm package name availability",
    ),
    "youtube": (
        "https://www.youtube.com/{}",
        "YouTube channel name availability",
    ),
}

for _name, (_template, _desc) in _PLATFORM_CHECKS.items():
    _func = _make_url_scorer(_template, _name, _desc)
    scorers.register(
        _name,
        cost="moderate",
        requires_network=True,
        latency="medium",
        parallelizable=True,
        description=_desc,
    )(_func)
