#!/usr/bin/env python3
"""Runner script for the research company brand name pipeline.

Executes a 4-stage funnel on ~80K DNS-verified CV3/VC3 names:

    Stage 1: Local brandability scoring + filter → top 2,000
    Stage 2: WHOIS .com verification → ~1,000
    Stage 3: US company name availability (OpenCorporates) → ~500
    Stage 4: LLM brand ranking (Claude) → top 100

Each stage persists results to disk, so the pipeline is resumable.

Usage
-----
    # Run from scratch (all stages)
    python misc/run_research_pipeline.py

    # Resume from a specific stage (e.g., skip Stage 1 if already done)
    python misc/run_research_pipeline.py --resume-from 2

    # Run only Stage 1 (local scoring — no network needed)
    python misc/run_research_pipeline.py --stop-after 1

    # Custom input file
    python misc/run_research_pipeline.py --input misc/dns_verified_cv3_and_vc3.txt

    # Custom project name (for resuming later)
    python misc/run_research_pipeline.py --project research_2026
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
_PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ_ROOT))

import brand
from brand.stages import Score, Filter
from brand.pipeline import (
    _project_dir,
    _stage_dir,
    _write_json,
    _read_json,
    _run_score,
    _run_filter,
)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_INPUT = _PROJ_ROOT / 'misc' / 'dns_verified_cv3_and_vc3.txt'
DEFAULT_CONTEXT = (
    "AI-enabled tools for sociology and health researchers, analysts, and clinicians"
)

# Stage definitions (explicit, not from template, for fine control)
STAGES = {
    1: {
        'name': 'local_scoring',
        'description': 'Score all names with cheap local brandability scorer, filter to top 2000',
        'score': Score(['brandability', 'name_length']),
        'filter': Filter(
            rules={
                'brandability': {'op': '>', 'value': 0.0},
                'name_length': {'op': '>=', 'value': 4},
            },
            top_n=2000,
            by='brandability',
        ),
    },
    2: {
        'name': 'whois_check',
        'description': 'WHOIS .com verification on surviving candidates',
        'score': Score(['whois_com']),
        'filter': Filter(rules={'whois_com': True}),
    },
    3: {
        'name': 'company_check',
        'description': 'US company name availability via OpenCorporates',
        'score': Score(['company_name_us']),
        'filter': Filter(rules={'company_name_us': True}),
    },
    4: {
        'name': 'llm_ranking',
        'description': 'LLM brand ranking via Claude → top 100',
        # Handled specially (batch LLM call, not per-name scoring)
    },
}


# ---------------------------------------------------------------------------
# Progress display
# ---------------------------------------------------------------------------


def _progress(msg: str, *, newline: bool = True):
    ts = datetime.now().strftime('%H:%M:%S')
    end = '\n' if newline else '\r'
    print(f'[{ts}] {msg}', end=end, flush=True)


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------


def run_stage_1(candidates: list[dict], proj_dir: str) -> list[dict]:
    """Stage 1: Local brandability scoring → top 2000."""
    _progress(f'Stage 1: Scoring {len(candidates)} names with brandability scorer...')

    stage_def = STAGES[1]
    t0 = time.time()

    # Score in chunks with progress reporting
    chunk_size = 5000
    for i in range(0, len(candidates), chunk_size):
        chunk_end = min(i + chunk_size, len(candidates))
        chunk = candidates[i:chunk_end]
        _run_score(stage_def['score'], chunk)
        _progress(
            f'  Scored {chunk_end}/{len(candidates)} '
            f'({chunk_end * 100 // len(candidates)}%)',
            newline=False,
        )
    print()  # newline after progress

    elapsed = time.time() - t0
    _progress(f'  Scoring complete in {elapsed:.1f}s')

    # Save pre-filter results
    sdir = _stage_dir(proj_dir, 0, 'score')
    _write_json(os.path.join(sdir, 'results.json'), candidates)

    # Filter
    _progress(f'  Filtering to top 2000 by brandability...')
    filtered = _run_filter(stage_def['filter'], candidates)

    # Save post-filter results
    sdir = _stage_dir(proj_dir, 1, 'filter')
    _write_json(
        os.path.join(sdir, 'results.json'),
        {'before': len(candidates), 'after': len(filtered), 'candidates': filtered},
    )

    top_score = filtered[0]['scores']['brandability'] if filtered else 0
    bottom_score = filtered[-1]['scores']['brandability'] if filtered else 0
    _progress(
        f'  Stage 1 done: {len(candidates)} → {len(filtered)} '
        f'(brandability range: {bottom_score:.4f}–{top_score:.4f})'
    )
    return filtered


def run_stage_2(candidates: list[dict], proj_dir: str) -> list[dict]:
    """Stage 2: WHOIS .com verification."""
    _progress(f'Stage 2: WHOIS checking {len(candidates)} names...')

    stage_def = STAGES[2]
    t0 = time.time()

    # WHOIS is network-based and parallelizable — the pipeline handles this
    candidates = _run_score(stage_def['score'], candidates)

    elapsed = time.time() - t0
    _progress(f'  WHOIS scoring complete in {elapsed:.1f}s')

    sdir = _stage_dir(proj_dir, 2, 'score')
    _write_json(os.path.join(sdir, 'results.json'), candidates)

    # Filter to whois-available only
    filtered = _run_filter(stage_def['filter'], candidates)

    sdir = _stage_dir(proj_dir, 3, 'filter')
    _write_json(
        os.path.join(sdir, 'results.json'),
        {'before': len(candidates), 'after': len(filtered), 'candidates': filtered},
    )

    _progress(f'  Stage 2 done: {len(candidates)} → {len(filtered)} whois-available')
    return filtered


def run_stage_3(candidates: list[dict], proj_dir: str) -> list[dict]:
    """Stage 3: US company name availability."""
    _progress(f'Stage 3: Checking US company name availability for {len(candidates)} names...')

    stage_def = STAGES[3]
    t0 = time.time()

    candidates = _run_score(stage_def['score'], candidates)

    elapsed = time.time() - t0
    _progress(f'  Company name check complete in {elapsed:.1f}s')

    sdir = _stage_dir(proj_dir, 4, 'score')
    _write_json(os.path.join(sdir, 'results.json'), candidates)

    # Filter to company-name-available only
    filtered = _run_filter(stage_def['filter'], candidates)

    sdir = _stage_dir(proj_dir, 5, 'filter')
    _write_json(
        os.path.join(sdir, 'results.json'),
        {'before': len(candidates), 'after': len(filtered), 'candidates': filtered},
    )

    _progress(f'  Stage 3 done: {len(candidates)} → {len(filtered)} company-available')
    return filtered


def run_stage_4(
    candidates: list[dict],
    proj_dir: str,
    *,
    context: str = DEFAULT_CONTEXT,
) -> list[dict]:
    """Stage 4: LLM brand ranking → top 100."""
    _progress(f'Stage 4: LLM ranking {len(candidates)} names with Claude...')

    from brand._scorers.llm import llm_brand_rating_batch, get_usage_summary

    t0 = time.time()
    names = [c['name'] for c in candidates]

    # Batch call to Claude (25 names/batch to fit in output token limit)
    ratings = llm_brand_rating_batch(names, context=context, batch_size=25)

    # Merge ratings into candidates
    for cand in candidates:
        rating = ratings.get(cand['name'].lower(), {})
        cand['scores']['llm_brand_rating'] = rating
        # Extract overall score for sorting
        overall = rating.get('overall', 0)
        if isinstance(overall, (int, float)):
            cand['scores']['llm_overall'] = float(overall)
        else:
            cand['scores']['llm_overall'] = 0.0

    elapsed = time.time() - t0
    _progress(f'  LLM rating complete in {elapsed:.1f}s')

    sdir = _stage_dir(proj_dir, 6, 'score')
    _write_json(os.path.join(sdir, 'results.json'), candidates)

    # Sort by LLM overall score and take top 100
    candidates.sort(key=lambda c: c['scores'].get('llm_overall', 0), reverse=True)
    top_100 = candidates[:100]

    sdir = _stage_dir(proj_dir, 7, 'filter')
    _write_json(
        os.path.join(sdir, 'results.json'),
        {'before': len(candidates), 'after': len(top_100), 'candidates': top_100},
    )

    # Report token usage
    usage = get_usage_summary()
    _progress(f'  LLM usage: {usage["api_calls"]} API calls, '
              f'{usage["total_input_tokens"]:,} input + {usage["total_output_tokens"]:,} output tokens')
    _progress(f'  Estimated cost: ${usage["estimated_cost_usd"]:.4f}')

    sdir_usage = _stage_dir(proj_dir, 8, 'usage')
    _write_json(os.path.join(sdir_usage, 'llm_usage.json'), usage)

    _progress(f'  Stage 4 done: {len(candidates)} → {len(top_100)} final candidates')
    return top_100


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------


def write_final_results(candidates: list[dict], proj_dir: str):
    """Write the final ranked list in multiple formats."""
    final_dir = os.path.join(proj_dir, 'final')
    os.makedirs(final_dir, exist_ok=True)

    # Full JSON
    _write_json(os.path.join(final_dir, 'results.json'), candidates)

    # Human-readable summary
    lines = ['# Top 100 Brand Name Candidates\n']
    lines.append(f'Generated: {datetime.now().isoformat()}\n')
    lines.append(f'| Rank | Name | Brandability | LLM Overall | Rationale |')
    lines.append(f'|------|------|-------------|-------------|-----------|')

    for i, cand in enumerate(candidates, 1):
        name = cand['name']
        brand_score = cand['scores'].get('brandability', '-')
        llm = cand['scores'].get('llm_brand_rating', {})
        llm_overall = llm.get('overall', '-')
        rationale = llm.get('rationale', '-')
        lines.append(f'| {i} | {name} | {brand_score} | {llm_overall} | {rationale} |')

    summary_path = os.path.join(final_dir, 'top_100.md')
    with open(summary_path, 'w') as f:
        f.write('\n'.join(lines))

    # Simple name list
    names_path = os.path.join(final_dir, 'top_100_names.txt')
    with open(names_path, 'w') as f:
        for cand in candidates:
            f.write(cand['name'] + '\n')

    _progress(f'Final results written to {final_dir}/')
    _progress(f'  {summary_path}')
    _progress(f'  {names_path}')


# ---------------------------------------------------------------------------
# Load / resume helpers
# ---------------------------------------------------------------------------


def load_names(path: str) -> list[str]:
    """Load names from a text file (one per line)."""
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def load_stage_results(proj_dir: str, stage_index: int) -> list[dict] | None:
    """Try to load results from a completed stage."""
    # Look for filter stage results (they contain 'candidates')
    for d in sorted(os.listdir(proj_dir)):
        if d.startswith(f'stage_{stage_index:02d}_filter'):
            path = os.path.join(proj_dir, d, 'results.json')
            if os.path.exists(path):
                data = _read_json(path)
                if isinstance(data, dict) and 'candidates' in data:
                    return data['candidates']
                return data
    # Also check score stages
    for d in sorted(os.listdir(proj_dir)):
        if d.startswith(f'stage_{stage_index:02d}_score'):
            path = os.path.join(proj_dir, d, 'results.json')
            if os.path.exists(path):
                return _read_json(path)
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description='Run the research company brand name pipeline',
    )
    parser.add_argument(
        '--input',
        default=str(DEFAULT_INPUT),
        help='Input file with one name per line (default: dns_verified_cv3_and_vc3.txt)',
    )
    parser.add_argument(
        '--project',
        default=None,
        help='Project name (default: auto-generated timestamp)',
    )
    parser.add_argument(
        '--resume-from',
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help='Stage to resume from (1-4, default: 1)',
    )
    parser.add_argument(
        '--stop-after',
        type=int,
        default=4,
        choices=[1, 2, 3, 4],
        help='Stage to stop after (1-4, default: 4)',
    )
    parser.add_argument(
        '--context',
        default=DEFAULT_CONTEXT,
        help='Company context for LLM ranking',
    )
    parser.add_argument(
        '--top-n-stage1',
        type=int,
        default=2000,
        help='How many names to keep after Stage 1 (default: 2000)',
    )

    args = parser.parse_args()

    # Override Stage 1 top_n if specified
    if args.top_n_stage1 != 2000:
        STAGES[1]['filter'] = Filter(
            rules={
                'brandability': {'op': '>', 'value': 0.0},
                'name_length': {'op': '>=', 'value': 4},
            },
            top_n=args.top_n_stage1,
            by='brandability',
        )

    # Set up project directory
    proj_dir = _project_dir(args.project)
    _progress(f'Project directory: {proj_dir}')

    # Save pipeline config
    _write_json(
        os.path.join(proj_dir, 'pipeline_config.json'),
        {
            'input': args.input,
            'context': args.context,
            'resume_from': args.resume_from,
            'stop_after': args.stop_after,
            'top_n_stage1': args.top_n_stage1,
            'started': datetime.now().isoformat(),
        },
    )

    candidates = None

    # --- Stage 1 ---
    if args.resume_from <= 1 and args.stop_after >= 1:
        names = load_names(args.input)
        _progress(f'Loaded {len(names)} names from {args.input}')
        candidates = [{'name': n, 'scores': {}} for n in names]
        candidates = run_stage_1(candidates, proj_dir)
    elif args.resume_from > 1:
        # Load from previous stage's filter output
        # Stage 1 filter is at stage index 1
        candidates = load_stage_results(proj_dir, 1)
        if candidates is None:
            _progress('ERROR: Cannot resume — no Stage 1 results found in project dir')
            _progress(f'  Looked in: {proj_dir}')
            sys.exit(1)
        _progress(f'Resumed with {len(candidates)} candidates from Stage 1')

    # --- Stage 2 ---
    if args.resume_from <= 2 and args.stop_after >= 2 and candidates is not None:
        candidates = run_stage_2(candidates, proj_dir)
    elif args.resume_from > 2:
        candidates = load_stage_results(proj_dir, 3)
        if candidates is None:
            _progress('ERROR: Cannot resume — no Stage 2 results found')
            sys.exit(1)
        _progress(f'Resumed with {len(candidates)} candidates from Stage 2')

    # --- Stage 3 ---
    if args.resume_from <= 3 and args.stop_after >= 3 and candidates is not None:
        candidates = run_stage_3(candidates, proj_dir)
    elif args.resume_from > 3:
        candidates = load_stage_results(proj_dir, 5)
        if candidates is None:
            _progress('ERROR: Cannot resume — no Stage 3 results found')
            sys.exit(1)
        _progress(f'Resumed with {len(candidates)} candidates from Stage 3')

    # --- Stage 4 ---
    if args.resume_from <= 4 and args.stop_after >= 4 and candidates is not None:
        candidates = run_stage_4(candidates, proj_dir, context=args.context)

    # --- Final output ---
    if candidates is not None:
        write_final_results(candidates, proj_dir)
        _progress(f'Pipeline complete! {len(candidates)} final candidates.')
    else:
        _progress('No candidates to output.')


if __name__ == '__main__':
    main()
