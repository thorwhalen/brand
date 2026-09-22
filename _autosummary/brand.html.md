# brand

Brand: a composable pipeline for brand name generation, evaluation, and availability checking.

## Quick start

```pycon
>>> import brand
>>> result = brand.evaluate_name('figiri')
>>> result['scores']['syllables']
3
```

Browse available components:

```pycon
>>> list(brand.scorers)
['syllables', 'phonotactic', 'dns_com', ...]
>>> list(brand.generators)
['cvcvcv', 'ai_suggest', ...]
>>> list(brand.templates)
['tech_startup', 'python_package', 'quick_screen', ...]
```

Run a pre-configured pipeline:

```pycon
>>> results = brand.run_pipeline(
...     'tech_startup',
...     names=['figiri', 'lumex', 'voxen'],
... )
```

### Modules

| [`base`](brand.base.html.md#module-brand.base)           | Base functions for brand                                                |
|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`config`](brand.config.html.md#module-brand.config)       | Configuration for the brand package.                                    |
| [`misc`](brand.misc.html.md#module-brand.misc)           | Misc tools                                                              |
| [`pipeline`](brand.pipeline.html.md#module-brand.pipeline)   | Pipeline engine: run, persist, resume, and branch evaluation pipelines. |
| [`registry`](brand.registry.html.md#module-brand.registry)   | Discoverable, extensible component registries for brand.                |
| [`stages`](brand.stages.html.md#module-brand.stages)       | Pipeline stage definitions: Generate, Score, Filter.                    |
| [`templates`](brand.templates.html.md#module-brand.templates) | Pipeline templates — pre-configured pipelines for common use cases.     |
| [`util`](brand.util.html.md#module-brand.util)           | Util functions                                                          |
