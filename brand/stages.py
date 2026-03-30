"""Pipeline stage definitions: Generate, Score, Filter.

Stages are simple dataclasses that describe *what* to do at each step of a
pipeline.  They are serializable to/from dicts (and therefore JSON) so that
pipeline definitions can be persisted and replayed.
"""

from dataclasses import dataclass, field, asdict


# ---------------------------------------------------------------------------
# Stage types
# ---------------------------------------------------------------------------


@dataclass
class Generate:
    """Produce candidate names.

    Parameters
    ----------
    generator : str
        Name of a registered generator (e.g. ``'cvcvcv'``, ``'ai_suggest'``).
    params : dict
        Keyword arguments forwarded to the generator function.

    Examples
    --------
    >>> g = Generate('cvcvcv', params={'consonants': 'bdfglmnprstvz'})
    >>> g.to_dict()
    {'type': 'generate', 'generator': 'cvcvcv', 'params': {'consonants': 'bdfglmnprstvz'}}
    """

    generator: str
    params: dict = field(default_factory=dict)

    def to_dict(self):
        d = {"type": "generate", "generator": self.generator}
        if self.params:
            d["params"] = self.params
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(generator=d["generator"], params=d.get("params", {}))


@dataclass
class Score:
    """Compute one or more metrics on each candidate name.

    Parameters
    ----------
    scorers : list
        Each element is either a scorer name (str) or a ``(name, params_dict)``
        tuple for scorers that need configuration.

    Examples
    --------
    >>> s = Score(['phonotactic', 'syllables', ('dns', {'tlds': ['.com', '.io']})])
    >>> s.to_dict()['type']
    'score'
    """

    scorers: list = field(default_factory=list)

    def to_dict(self):
        serialized = []
        for s in self.scorers:
            if isinstance(s, str):
                serialized.append(s)
            else:
                name, params = s
                serialized.append({"name": name, "params": params})
        return {"type": "score", "scorers": serialized}

    @classmethod
    def from_dict(cls, d):
        scorers = []
        for s in d.get("scorers", []):
            if isinstance(s, str):
                scorers.append(s)
            else:
                scorers.append((s["name"], s.get("params", {})))
        return cls(scorers=scorers)


@dataclass
class Filter:
    """Reduce the candidate set based on accumulated scores.

    Exactly one of ``top_n``, ``top_pct``, or ``rules`` should be set (or a
    combination).  Rules are dicts mapping scorer names to required values:

    * ``True``/``False`` — exact match (good for boolean scorers like availability)
    * A number — minimum threshold
    * A dict ``{"op": ">=", "value": 5}`` — comparison

    Parameters
    ----------
    top_n : int | None
        Keep the top *N* candidates by ``by`` scorer (or aggregate).
    top_pct : float | None
        Keep the top *P%* of candidates.
    by : str | None
        Scorer name to rank by. Defaults to ``'aggregate'``.
    rules : dict | None
        ``{scorer_name: required_value}`` mapping.

    Examples
    --------
    >>> f = Filter(rules={'dns_com': True})
    >>> f.to_dict()
    {'type': 'filter', 'rules': {'dns_com': True}}
    """

    top_n: int | None = None
    top_pct: float | None = None
    by: str | None = None
    rules: dict | None = None

    def to_dict(self):
        d = {"type": "filter"}
        if self.top_n is not None:
            d["top_n"] = self.top_n
        if self.top_pct is not None:
            d["top_pct"] = self.top_pct
        if self.by is not None:
            d["by"] = self.by
        if self.rules is not None:
            d["rules"] = self.rules
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(
            top_n=d.get("top_n"),
            top_pct=d.get("top_pct"),
            by=d.get("by"),
            rules=d.get("rules"),
        )


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

_STAGE_TYPES = {
    "generate": Generate,
    "score": Score,
    "filter": Filter,
}


def stage_from_dict(d: dict):
    """Deserialize a stage dict into its dataclass.

    >>> stage_from_dict({'type': 'generate', 'generator': 'cvcvcv'})
    Generate(generator='cvcvcv', params={})
    """
    stage_type = d.get("type")
    if stage_type not in _STAGE_TYPES:
        raise ValueError(
            f"Unknown stage type {stage_type!r}. Expected one of {list(_STAGE_TYPES)}"
        )
    return _STAGE_TYPES[stage_type].from_dict(d)


def stages_to_dicts(stages: list) -> list[dict]:
    """Serialize a list of stages to a list of dicts."""
    return [s.to_dict() for s in stages]


def stages_from_dicts(dicts: list[dict]) -> list:
    """Deserialize a list of dicts into stage objects."""
    return [stage_from_dict(d) for d in dicts]
