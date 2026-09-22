# brand.pipeline

Pipeline engine: run, persist, resume, and branch evaluation pipelines.

A pipeline is a list of stages (`Generate`, `Score`, `Filter`) that
takes a stream of candidate names and progressively enriches, scores, filters,
and narrows them.

Every run creates a project folder with intermediate artifacts at each stage,
allowing inspection, resumption, and branching.

### Functions

| [`evaluate_name`](#brand.pipeline.evaluate_name)(name, \*[, template, scorers])    | Evaluate a single name with a quick scorecard.   |
|--------------------------------------------------------------------------------------------------|--------------------------------------------------|
| [`list_templates`](#brand.pipeline.list_templates)()                                | List available pipeline template names.          |
| [`load_template`](#brand.pipeline.load_template)(name)                             | Load a pipeline template by name.                |
| [`run_pipeline`](#brand.pipeline.run_pipeline)(stages, \*[, names, context, ...]) | Execute a brand evaluation pipeline.             |

### brand.pipeline.evaluate_name(name, , template=None, scorers=None)

Evaluate a single name with a quick scorecard.

* **Parameters:**
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The candidate brand name.
  * **template** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Pipeline template to use. Defaults to `'quick_screen'`.
  * **scorers** ([`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Explicit list of scorer names. Overrides template.
* **Returns:**
  `{'name': str, 'scores': {...}}`
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### Examples

```pycon
>>> result = evaluate_name('figiri')
>>> 'syllables' in result['scores']
True
```

### brand.pipeline.list_templates()

List available pipeline template names.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> 'quick_screen' in list_templates()
True
```

### brand.pipeline.load_template(name)

Load a pipeline template by name.

Searches the built-in templates directory and returns a list of stage
objects.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

```pycon
>>> stages = load_template('quick_screen')
>>> len(stages) > 0
True
```

### brand.pipeline.run_pipeline(stages, , names=None, context=None, project_name=None, resume_from=None, pipeline_dir=None, on_stage_complete=None)

Execute a brand evaluation pipeline.

* **Parameters:**
  * **stages** ([*list*](https://docs.python.org/3/builtins/stdtypes.html#list) *|* [*str*](https://docs.python.org/3/builtins/stdtypes.html#str)) – A list of stage objects (Generate, Score, Filter), or a template name
    string to load from the templates registry.
  * **names** ([`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Pre-existing candidate names. If provided, skips the Generate stage.
  * **context** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Context string for AI generators and expert synthesis.
  * **project_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Name for the project folder. Auto-generated if not provided.
  * **resume_from** ([`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Stage index to resume from. Loads prior artifacts from disk.
  * **pipeline_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Override the default pipeline storage directory.
  * **on_stage_complete** (*callable* *|* *None*) – Callback `(stage_index, stage_type, n_candidates)` after each stage.
* **Returns:**
  `{'candidates': [...], 'project_dir': str, 'stages_completed': int}`
* **Return type:**
  [*dict*](https://docs.python.org/3/builtins/stdtypes.html#dict)

### Examples

```pycon
>>> from brand.stages import Generate, Score, Filter
>>> results = run_pipeline([
...     Generate('from_list', params={'names': ['alpha', 'beta', 'gamma']}),
...     Score(['syllables', 'name_length']),
... ])
>>> len(results['candidates'])
3
```
