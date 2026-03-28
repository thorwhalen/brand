"""Brand: a composable pipeline for brand name generation, evaluation, and availability checking.

Quick start
-----------
>>> import brand
>>> result = brand.evaluate_name('figiri')
>>> result['scores']['syllables']
3

Browse available components:

>>> list(brand.scorers)  # doctest: +SKIP
['syllables', 'phonotactic', 'dns_com', ...]
>>> list(brand.generators)  # doctest: +SKIP
['cvcvcv', 'ai_suggest', ...]
>>> list(brand.templates)  # doctest: +SKIP
['tech_startup', 'python_package', 'quick_screen', ...]

Run a pre-configured pipeline:

>>> results = brand.run_pipeline(  # doctest: +SKIP
...     'tech_startup',
...     names=['figiri', 'lumex', 'voxen'],
... )
"""

# -- Trigger auto-registration of built-in scorers and generators -------------
import brand._scorers  # noqa: F401
import brand._generators  # noqa: F401

# -- Registries (import these to discover/register components) ----------------
from brand.registry import scorers, generators, filters, pipelines

# -- Stage types (for building custom pipelines) ------------------------------
from brand.stages import Generate, Score, Filter

# -- Pipeline engine ----------------------------------------------------------
from brand.pipeline import run_pipeline, evaluate_name, load_template, list_templates

# -- Backward-compatible API from brand.base ----------------------------------
from brand.base import (
    is_available_as,
    domain_name_is_available,
    batch_check_available,
    english_words_gen,
    ask_ai_to_generate_names,
    ai_analyze_names,
)

# -- Convenience alias --------------------------------------------------------
templates = list_templates
