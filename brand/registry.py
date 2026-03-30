"""Discoverable, extensible component registries for brand."""

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass
class ComponentMeta:
    """Metadata for a registered component."""

    func: object  # Callable
    name: str
    cost: str = "cheap"  # 'cheap' | 'moderate' | 'expensive'
    requires_network: bool = False
    latency: str = "fast"  # 'fast' | 'medium' | 'slow'
    parallelizable: bool = True
    description: str = ""
    requires_extras: tuple = ()

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __repr__(self):
        tags = []
        if self.requires_network:
            tags.append("network")
        tags.append(self.cost)
        tags.append(self.latency)
        tag_str = ", ".join(tags)
        return f"<{self.name} ({tag_str})>"


class Registry(Mapping):
    """A discoverable, extensible registry of named components.

    Implements ``collections.abc.Mapping`` so you can iterate, index, and
    check membership just like a dict.

    Examples
    --------
    >>> r = Registry('scorers')
    >>> @r.register('length')
    ... def length_scorer(name):
    ...     return len(name)
    >>> list(r)
    ['length']
    >>> r['length']('hello')
    5
    >>> r['length'].cost
    'cheap'
    """

    def __init__(self, name: str):
        self._name = name
        self._items: dict[str, ComponentMeta] = {}

    # -- Registration ---------------------------------------------------------

    def register(
        self,
        name=None,
        *,
        cost="cheap",
        requires_network=False,
        latency="fast",
        parallelizable=True,
        description="",
        requires_extras=(),
    ):
        """Register a function. Usable as decorator with or without arguments.

        Examples
        --------
        >>> r = Registry('test')
        >>> @r.register
        ... def foo(x): return x
        >>> 'foo' in r
        True
        >>> @r.register('bar', cost='expensive')
        ... def bar_func(x): return x * 2
        >>> r['bar'].cost
        'expensive'
        """
        meta_kwargs = dict(
            cost=cost,
            requires_network=requires_network,
            latency=latency,
            parallelizable=parallelizable,
            description=description,
            requires_extras=requires_extras,
        )

        def decorator(func):
            key = name if isinstance(name, str) else func.__name__
            self._items[key] = ComponentMeta(func=func, name=key, **meta_kwargs)
            return func

        # @registry.register  (no parens, name is the function itself)
        if callable(name):
            func = name
            name_str = func.__name__
            self._items[name_str] = ComponentMeta(func=func, name=name_str)
            return func

        return decorator

    # -- Mapping interface ----------------------------------------------------

    def __getitem__(self, key: str) -> ComponentMeta:
        if key not in self._items:
            available = ", ".join(sorted(self._items))
            raise KeyError(
                f"No {self._name[:-1] if self._name.endswith('s') else self._name} "
                f"named {key!r}. Available: [{available}]"
            )
        return self._items[key]

    def __iter__(self):
        yield from self._items

    def __len__(self):
        return len(self._items)

    def __contains__(self, key):
        return key in self._items

    def __repr__(self):
        return f"Registry({self._name!r}, keys={list(self._items.keys())})"


# -- Global registries -------------------------------------------------------

scorers = Registry("scorers")
generators = Registry("generators")
filters = Registry("filters")
pipelines = Registry("pipelines")
