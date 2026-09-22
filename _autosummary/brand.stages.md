# brand.stages

Pipeline stage definitions: Generate, Score, Filter.

Stages are simple dataclasses that describe *what* to do at each step of a
pipeline.  They are serializable to/from dicts (and therefore JSON) so that
pipeline definitions can be persisted and replayed.

### Functions

| [`stage_from_dict`](#brand.stages.stage_from_dict)(d)       | Deserialize a stage dict into its dataclass.    |
|---------------------------------------------------------------------------|-------------------------------------------------|
| [`stages_from_dicts`](#brand.stages.stages_from_dicts)(dicts) | Deserialize a list of dicts into stage objects. |
| [`stages_to_dicts`](#brand.stages.stages_to_dicts)(stages)  | Serialize a list of stages to a list of dicts.  |

### Classes

| [`Filter`](#brand.stages.Filter)([top_n, top_pct, by, rules])   | Reduce the candidate set based on accumulated scores.   |
|----------------------------------------------------------------------------------------|---------------------------------------------------------|
| [`Generate`](#brand.stages.Generate)(generator[, params])         | Produce candidate names.                                |
| [`Score`](#brand.stages.Score)([scorers])                      | Compute one or more metrics on each candidate name.     |

### *class* brand.stages.Filter(top_n=None, top_pct=None, by=None, rules=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Reduce the candidate set based on accumulated scores.

Exactly one of `top_n`, `top_pct`, or `rules` should be set (or a
combination).  Rules are dicts mapping scorer names to required values:

* `True`/`False` — exact match (good for boolean scorers like availability)
* A number — minimum threshold
* A dict `{"op": ">=", "value": 5}` — comparison

* **Parameters:**
  * **top_n** ([`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Keep the top *N* candidates by `by` scorer (or aggregate).
  * **top_pct** ([`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Keep the top *P%* of candidates.
  * **by** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Scorer name to rank by. Defaults to `'aggregate'`.
  * **rules** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – `{scorer_name: required_value}` mapping.

### Examples

```pycon
>>> f = Filter(rules={'dns_com': True})
>>> f.to_dict()
{'type': 'filter', 'rules': {'dns_com': True}}
```

### *class* brand.stages.Generate(generator, params=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Produce candidate names.

* **Parameters:**
  * **generator** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of a registered generator (e.g. `'cvcvcv'`, `'ai_suggest'`).
  * **params** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)) – Keyword arguments forwarded to the generator function.

### Examples

```pycon
>>> g = Generate('cvcvcv', params={'consonants': 'bdfglmnprstvz'})
>>> g.to_dict()
{'type': 'generate', 'generator': 'cvcvcv', 'params': {'consonants': 'bdfglmnprstvz'}}
```

### *class* brand.stages.Score(scorers=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Compute one or more metrics on each candidate name.

* **Parameters:**
  **scorers** ([`list`](https://docs.python.org/3/builtins/stdtypes.html#list)) – Each element is either a scorer name (str) or a `(name, params_dict)`
  tuple for scorers that need configuration.

### Examples

```pycon
>>> s = Score(['phonotactic', 'syllables', ('dns', {'tlds': ['.com', '.io']})])
>>> s.to_dict()['type']
'score'
```

### brand.stages.stage_from_dict(d)

Deserialize a stage dict into its dataclass.

```pycon
>>> stage_from_dict({'type': 'generate', 'generator': 'cvcvcv'})
Generate(generator='cvcvcv', params={})
```

### brand.stages.stages_from_dicts(dicts)

Deserialize a list of dicts into stage objects.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

### brand.stages.stages_to_dicts(stages)

Serialize a list of stages to a list of dicts.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]
