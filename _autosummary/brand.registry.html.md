# brand.registry

Discoverable, extensible component registries for brand.

### Classes

| [`ComponentMeta`](#brand.registry.ComponentMeta)(func, name[, cost, ...])   | Metadata for a registered component.                     |
|-------------------------------------------------------------------------------------------|----------------------------------------------------------|
| [`Registry`](#brand.registry.Registry)(name)                           | A discoverable, extensible registry of named components. |

### *class* brand.registry.ComponentMeta(func, name, cost='cheap', requires_network=False, latency='fast', parallelizable=True, description='', requires_extras=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Metadata for a registered component.

### *class* brand.registry.Registry(name)

Bases: [`Mapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)

A discoverable, extensible registry of named components.

Implements `collections.abc.Mapping` so you can iterate, index, and
check membership just like a dict.

### Examples

```pycon
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
```

#### register(name=None, , cost='cheap', requires_network=False, latency='fast', parallelizable=True, description='', requires_extras=())

Register a function. Usable as decorator with or without arguments.

### Examples

```pycon
>>> r = Registry('test')
>>> @r.register
... def foo(x): return x
>>> 'foo' in r
True
>>> @r.register('bar', cost='expensive')
... def bar_func(x): return x * 2
>>> r['bar'].cost
'expensive'
```
