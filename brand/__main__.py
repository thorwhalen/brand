"""Command line for brand: ``python -m brand domains NAME... [--tlds com,io] [--json]``.

Checks whether each ``NAME.TLD`` is registered, asking the registry (DNS, RDAP,
WHOIS) and never a registrar's search page.  A NAME that already contains a dot
is checked as given.  Prints one row per domain with its verdict (free / taken /
unknown), the pass that decided it and the UTC time of the check.  Exits 0 when
at least one domain is free.
"""

import argparse
import json
import sys
from collections.abc import Sequence

VERDICTS = {True: "free", False: "taken", None: "unknown"}


def _domains(names: Sequence[str], tlds: Sequence[str]) -> list[str]:
    """``name.tld`` for every pair, keeping a name that already has a dot as is.

    >>> _domains(["foo", "bar.fr"], ["com", "io"])
    ['foo.com', 'foo.io', 'bar.fr']
    """
    return [d for n in names for d in ([n] if "." in n else [f"{n}.{t}" for t in tlds])]


def _render(rows: Sequence[dict]) -> str:
    head = ["domain", "verdict", "source", "checked_utc"]
    body = [
        [r["domain"], r["verdict"], r["source"] or "-", r["checked_utc"]] for r in rows
    ]
    widths = [max(len(c) for c in col) for col in zip(head, *body)]
    return "\n".join(
        "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()
        for cells in [head, *body]
    )


def domains(argv: Sequence[str] | None = None, *, check=None) -> int:
    """The ``domains`` command; *check* defaults to ``check_domain`` (a seam for tests)."""
    from brand._scorers.availability import DEFAULT_DOMAIN_TLDS, check_domain

    check = check or check_domain
    ap = argparse.ArgumentParser(
        prog="python -m brand domains", description=__doc__.split("\n")[0]
    )
    ap.add_argument("names", nargs="+")
    ap.add_argument(
        "--tlds", default=",".join(DEFAULT_DOMAIN_TLDS), help="comma list, no dots"
    )
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    tlds = [t.strip().lstrip(".") for t in a.tlds.split(",") if t.strip()]
    rows = [
        {**r, "verdict": VERDICTS[r["available"]]}
        for r in map(check, _domains(a.names, tlds))
    ]
    print(json.dumps(rows, indent=2) if a.json else _render(rows))
    return 0 if any(r["available"] is True for r in rows) else 1


COMMANDS = {"domains": domains}


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in COMMANDS:
        print(f"usage: python -m brand {{{','.join(COMMANDS)}}} ...", file=sys.stderr)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
