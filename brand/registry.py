"""Discoverable, extensible component registries for brand."""

import inspect
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field


_ON_DUPLICATE = ("warn", "raise", "overwrite")


def _identity(func) -> str:
    return f"{getattr(func, '__module__', '?')}.{getattr(func, '__qualname__', repr(func))}"


def _same_function(a, b) -> bool:
    """Same object, or a reloaded module-level function of the same dotted name."""
    if a is b:
        return True
    if not (inspect.isfunction(a) and inspect.isfunction(b)):
        return False
    ident = _identity(a)
    return ident == _identity(b) and "<" not in ident


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
    rate_limit: float | None = None  # max requests/second across all threads
    max_workers: int | None = None  # thread-pool size; None = pipeline default

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

    def __init__(self, name: str, *, on_duplicate: str = "warn"):
        self._name = name
        self.on_duplicate = on_duplicate
        self._items: dict[str, ComponentMeta] = {}

    @property
    def on_duplicate(self) -> str:
        """What registering a different function under a taken name does: one of
        ``"warn"`` (default), ``"raise"``, ``"overwrite"``. Assignable.

        >>> r = Registry('s')
        >>> r.on_duplicate = 'raise'
        >>> r.on_duplicate
        'raise'
        """
        return self._on_duplicate

    @on_duplicate.setter
    def on_duplicate(self, policy: str):
        if policy not in _ON_DUPLICATE:
            raise ValueError(f"on_duplicate must be one of {_ON_DUPLICATE}")
        self._on_duplicate = policy

    def unregister(self, name: str) -> ComponentMeta:
        """Remove ``name`` and return what was registered under it (KeyError if absent).

        >>> r = Registry('s')
        >>> _ = r.register('x')(len)
        >>> r.unregister('x').func is len, 'x' in r
        (True, False)
        """
        try:
            return self._items.pop(name)
        except KeyError:
            raise KeyError(
                f"{self._name} has no {name!r}; available: {', '.join(sorted(self._items))}"
            ) from None

    def _add(self, key: str, func, *, stacklevel: int = 3, **meta_kwargs):
        """Store ``func`` under ``key``, applying the ``on_duplicate`` policy.

        Re-registering the same module-level function (e.g. a module reload) is silent;
        closures made in a factory are not recognised as the same.

        >>> r = Registry('scorers')
        >>> r.register('x')(lambda n: 1) and None
        >>> import warnings
        >>> with warnings.catch_warnings(record=True) as w:
        ...     warnings.simplefilter('always')
        ...     _ = r.register('x')(lambda n: 2)
        >>> len(w)
        1
        >>> Registry('s', on_duplicate='raise').register('x')(len) is len
        True
        """
        old = self._items.get(key)
        if old is not None and not _same_function(old.func, func):
            msg = (
                f"{self._name} already has {key!r} ({_identity(old.func)}); "
                f"replacing it with {_identity(func)}"
            )
            if self._on_duplicate == "raise":
                raise ValueError(msg)
            if self._on_duplicate == "warn":
                warnings.warn(msg, stacklevel=stacklevel)
        self._items[key] = ComponentMeta(func=func, name=key, **meta_kwargs)

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
        rate_limit=None,
        max_workers=None,
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
            rate_limit=rate_limit,
            max_workers=max_workers,
        )

        bare = callable(name)

        def decorator(func):
            key = name if isinstance(name, str) else func.__name__
            self._add(key, func, stacklevel=4 if bare else 3, **meta_kwargs)
            return func

        # @registry.register  (no parens, name is the function itself)
        if callable(name):
            return decorator(name)

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
