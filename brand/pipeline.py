"""Pipeline engine: run, persist, resume, and branch evaluation pipelines.

A pipeline is a list of stages (``Generate``, ``Score``, ``Filter``) that
takes a stream of candidate names and progressively enriches, scores, filters,
and narrows them.

Every run creates a project folder with intermediate artifacts at each stage,
allowing inspection, resumption, and branching.
"""

import json
import os
import math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from brand.config import PIPELINES_DIR
from brand.registry import scorers as scorer_registry, generators as generator_registry
from brand.stages import Generate, Score, Filter, stages_to_dicts, stages_from_dicts


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _project_dir(project_name: str | None, *, pipeline_dir: str | None = None) -> str:
    """Create and return the project directory path."""
    base = pipeline_dir or PIPELINES_DIR
    if project_name is None:
        project_name = datetime.now().strftime('run_%Y%m%d_%H%M%S')
    path = os.path.join(base, project_name)
    os.makedirs(path, exist_ok=True)
    return path


def _stage_dir(project_path: str, stage_index: int, stage_type: str) -> str:
    """Create and return the directory for a specific stage."""
    dirname = f"stage_{stage_index:02d}_{stage_type}"
    path = os.path.join(project_path, dirname)
    os.makedirs(path, exist_ok=True)
    return path


def _write_json(path: str, data):
    """Write data as pretty-printed JSON."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def _read_json(path: str):
    """Read JSON data from a file."""
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Stage execution
# ---------------------------------------------------------------------------


def _run_generate(stage: Generate, *, context: str | None = None) -> list[str]:
    """Execute a Generate stage, returning a list of candidate names."""
    gen_meta = generator_registry[stage.generator]
    params = dict(stage.params)

    # Inject context if the generator accepts it and context is provided
    if context and 'context' in gen_meta.func.__code__.co_varnames:
        params.setdefault('context', context)

    result = gen_meta.func(**params)
    # Materialize iterables
    return list(result)


def _run_score(
    stage: Score,
    candidates: list[dict],
) -> list[dict]:
    """Execute a Score stage, enriching each candidate's scores dict."""
    for scorer_spec in stage.scorers:
        if isinstance(scorer_spec, str):
            scorer_name, scorer_params = scorer_spec, {}
        else:
            scorer_name, scorer_params = scorer_spec

        scorer_meta = scorer_registry[scorer_name]

        # Decide parallelism
        if scorer_meta.parallelizable and scorer_meta.requires_network:
            candidates = _score_parallel(
                candidates, scorer_name, scorer_meta, scorer_params
            )
        else:
            for cand in candidates:
                try:
                    result = scorer_meta.func(cand['name'], **scorer_params)
                except Exception as e:
                    result = {'error': f"{type(e).__name__}: {e}"}
                cand['scores'][scorer_name] = result

    return candidates


def _score_parallel(
    candidates: list[dict],
    scorer_name: str,
    scorer_meta,
    scorer_params: dict,
    *,
    max_workers: int = 10,
) -> list[dict]:
    """Score candidates in parallel using a thread pool."""

    def _score_one(cand):
        try:
            result = scorer_meta.func(cand['name'], **scorer_params)
        except Exception as e:
            result = {'error': f"{type(e).__name__}: {e}"}
        return cand['name'], result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_score_one, c): c for c in candidates}
        results = {}
        for future in as_completed(futures):
            name, result = future.result()
            results[name] = result

    for cand in candidates:
        cand['scores'][scorer_name] = results.get(cand['name'])

    return candidates


def _compute_aggregate(scores: dict) -> float:
    """Compute a simple aggregate score from a scores dict.

    Booleans are converted to 1.0/0.0.  Dicts and lists are skipped.
    Non-numeric values are ignored.
    """
    values = []
    for v in scores.values():
        if isinstance(v, bool):
            values.append(1.0 if v else 0.0)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            values.append(float(v))
    return sum(values) / len(values) if values else 0.0


def _run_filter(stage: Filter, candidates: list[dict]) -> list[dict]:
    """Execute a Filter stage, reducing the candidate list."""
    result = candidates

    # Apply rules first
    if stage.rules:
        result = _apply_rules(result, stage.rules)

    # Apply top_n / top_pct
    if stage.top_n is not None or stage.top_pct is not None:
        sort_key = stage.by or 'aggregate'

        def _sort_value(cand):
            if sort_key == 'aggregate':
                return _compute_aggregate(cand['scores'])
            val = cand['scores'].get(sort_key, 0)
            if isinstance(val, bool):
                return 1.0 if val else 0.0
            if isinstance(val, (int, float)):
                return float(val)
            return 0.0

        result = sorted(result, key=_sort_value, reverse=True)

        if stage.top_n is not None:
            result = result[: stage.top_n]
        elif stage.top_pct is not None:
            n = max(1, math.ceil(len(result) * stage.top_pct / 100.0))
            result = result[:n]

    return result


def _apply_rules(candidates: list[dict], rules: dict) -> list[dict]:
    """Filter candidates by score rules.

    Rules map scorer names to expected values:
    - True/False: exact boolean match
    - number: minimum threshold
    - dict with 'op' and 'value': comparison
    """
    result = []
    for cand in candidates:
        keep = True
        for scorer_name, expected in rules.items():
            actual = cand['scores'].get(scorer_name)
            if actual is None:
                keep = False
                break
            if isinstance(expected, bool):
                if actual != expected:
                    keep = False
                    break
            elif isinstance(expected, (int, float)):
                if not isinstance(actual, (int, float)):
                    keep = False
                    break
                if actual < expected:
                    keep = False
                    break
            elif isinstance(expected, dict):
                op = expected.get('op', '>=')
                val = expected.get('value', 0)
                if not _compare(actual, op, val):
                    keep = False
                    break
        if keep:
            result.append(cand)
    return result


def _compare(actual, op: str, value) -> bool:
    """Apply a comparison operator."""
    ops = {
        '>=': lambda a, b: a >= b,
        '<=': lambda a, b: a <= b,
        '>': lambda a, b: a > b,
        '<': lambda a, b: a < b,
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
    }
    return ops.get(op, ops['>='])(actual, value)


# ---------------------------------------------------------------------------
# Main pipeline runner
# ---------------------------------------------------------------------------


def run_pipeline(
    stages,
    *,
    names: list[str] | None = None,
    context: str | None = None,
    project_name: str | None = None,
    resume_from: int | None = None,
    pipeline_dir: str | None = None,
    on_stage_complete=None,
):
    """Execute a brand evaluation pipeline.

    Parameters
    ----------
    stages : list | str
        A list of stage objects (Generate, Score, Filter), or a template name
        string to load from the templates registry.
    names : list[str] | None
        Pre-existing candidate names. If provided, skips the Generate stage.
    context : str | None
        Context string for AI generators and expert synthesis.
    project_name : str | None
        Name for the project folder. Auto-generated if not provided.
    resume_from : int | None
        Stage index to resume from. Loads prior artifacts from disk.
    pipeline_dir : str | None
        Override the default pipeline storage directory.
    on_stage_complete : callable | None
        Callback ``(stage_index, stage_type, n_candidates)`` after each stage.

    Returns
    -------
    dict
        ``{'candidates': [...], 'project_dir': str, 'stages_completed': int}``

    Examples
    --------
    >>> from brand.stages import Generate, Score, Filter
    >>> results = run_pipeline([
    ...     Generate('from_list', params={'names': ['alpha', 'beta', 'gamma']}),
    ...     Score(['syllables', 'name_length']),
    ... ])
    >>> len(results['candidates'])
    3
    """
    # Handle template name
    if isinstance(stages, str):
        stages = load_template(stages)

    # Set up project directory
    proj_dir = _project_dir(project_name, pipeline_dir=pipeline_dir)

    # Save pipeline definition
    _write_json(
        os.path.join(proj_dir, 'pipeline.json'),
        {'stages': stages_to_dicts(stages), 'context': context},
    )

    # Initialize candidates
    candidates = None

    if resume_from is not None and resume_from > 0:
        # Load candidates from previous stage
        prev_stage_idx = resume_from - 1
        prev_dirs = sorted(
            d
            for d in os.listdir(proj_dir)
            if d.startswith(f'stage_{prev_stage_idx:02d}_')
        )
        if prev_dirs:
            prev_path = os.path.join(proj_dir, prev_dirs[0], 'results.json')
            if os.path.exists(prev_path):
                candidates = _read_json(prev_path)
        if candidates is None:
            raise FileNotFoundError(
                f"Cannot resume from stage {resume_from}: "
                f"no artifacts found for stage {prev_stage_idx} in {proj_dir}"
            )
    elif names is not None:
        candidates = [{'name': n, 'scores': {}} for n in names]

    # Run stages
    start_idx = resume_from or 0

    for i, stage in enumerate(stages[start_idx:], start=start_idx):
        if isinstance(stage, Generate):
            if candidates is not None:
                # Already have candidates, skip generate
                continue
            raw_names = _run_generate(stage, context=context)
            candidates = [{'name': n, 'scores': {}} for n in raw_names]

            sdir = _stage_dir(proj_dir, i, 'generate')
            _write_json(
                os.path.join(sdir, 'results.json'),
                {'names': raw_names, 'count': len(raw_names)},
            )

        elif isinstance(stage, Score):
            if candidates is None:
                raise ValueError(
                    f"Score stage at index {i} has no candidates. "
                    "A Generate stage or 'names' parameter is required first."
                )
            candidates = _run_score(stage, candidates)

            sdir = _stage_dir(proj_dir, i, 'score')
            _write_json(os.path.join(sdir, 'results.json'), candidates)

        elif isinstance(stage, Filter):
            if candidates is None:
                raise ValueError(f"Filter stage at index {i} has no candidates.")
            before_count = len(candidates)
            candidates = _run_filter(stage, candidates)
            after_count = len(candidates)

            sdir = _stage_dir(proj_dir, i, 'filter')
            _write_json(
                os.path.join(sdir, 'results.json'),
                {
                    'before': before_count,
                    'after': after_count,
                    'candidates': candidates,
                },
            )

        if on_stage_complete:
            on_stage_complete(i, type(stage).__name__.lower(), len(candidates))

    # Write final results
    final_dir = os.path.join(proj_dir, 'final')
    os.makedirs(final_dir, exist_ok=True)
    _write_json(os.path.join(final_dir, 'results.json'), candidates)

    return {
        'candidates': candidates,
        'project_dir': proj_dir,
        'stages_completed': len(stages),
    }


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------


def load_template(name: str) -> list:
    """Load a pipeline template by name.

    Searches the built-in templates directory and returns a list of stage
    objects.

    >>> stages = load_template('quick_screen')
    >>> len(stages) > 0
    True
    """
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

    # Try .json file
    json_path = os.path.join(templates_dir, f'{name}.json')
    if os.path.exists(json_path):
        data = _read_json(json_path)
        stage_dicts = data.get('stages', data) if isinstance(data, dict) else data
        return stages_from_dicts(stage_dicts)

    raise FileNotFoundError(
        f"No template named {name!r}. "
        f"Available templates: {list_templates()}"
    )


def list_templates() -> list[str]:
    """List available pipeline template names.

    >>> 'quick_screen' in list_templates()
    True
    """
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.isdir(templates_dir):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(templates_dir)
        if f.endswith('.json') and not f.startswith('_')
    )


# ---------------------------------------------------------------------------
# Convenience: evaluate a single name
# ---------------------------------------------------------------------------


def evaluate_name(
    name: str,
    *,
    template: str | None = None,
    scorers: list[str] | None = None,
) -> dict:
    """Evaluate a single name with a quick scorecard.

    Parameters
    ----------
    name : str
        The candidate brand name.
    template : str | None
        Pipeline template to use. Defaults to ``'quick_screen'``.
    scorers : list[str] | None
        Explicit list of scorer names. Overrides template.

    Returns
    -------
    dict
        ``{'name': str, 'scores': {...}}``

    Examples
    --------
    >>> result = evaluate_name('figiri')
    >>> 'syllables' in result['scores']
    True
    """
    if scorers is not None:
        stages = [
            Generate('from_list', params={'names': [name]}),
            Score(scorers),
        ]
    elif template is not None:
        stages = load_template(template)
    else:
        # Default: quick local scoring
        stages = [
            Generate('from_list', params={'names': [name]}),
            Score([
                'syllables',
                'stress_pattern',
                'spelling_transparency',
                'sound_symbolism',
                'novelty',
                'substring_hazards',
                'letter_balance',
                'keyboard_distance',
                'name_length',
            ]),
        ]

    result = run_pipeline(stages, names=[name])
    if result['candidates']:
        return result['candidates'][0]
    return {'name': name, 'scores': {}}
