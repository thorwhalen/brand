---
name: brand-name-report
description: >
  Generate a comprehensive brand name analysis report for a list of candidate names.
  Computes all available metrics from the brand package, launches parallel AI agents
  for individual name deep-dives, and compiles a formatted markdown report.
  Use when the user provides candidate brand names and wants a comparative analysis.
argument-hint: <name1> <name2> ... [--context "company description"] [--output path] [--languages en,fr]
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Agent
---

# Brand Name Analysis Report

Generate a deep-dive comparative report for candidate brand names using the
`brand` package scorers and parallel AI analysis.

## Quick Reference

```
/brand-name-report dynody panapy ilumin --context "AI health tools" --output ~/Downloads/report.md
```

## What This Skill Does

1. **Computes all available metrics** from the `brand` Python package
2. **Launches parallel AI agents** (one per name) for qualitative analysis
3. **Compiles a formatted markdown report** with tables, per-name deep-dives, and appendices

## Workflow

### Phase 1: Parse Arguments

Extract from `$ARGUMENTS`:
- **Names**: all bare words (not prefixed with `--`)
- **`--context`**: company description for LLM prompts (default: "AI-enabled tools for health researchers, analysts, and clinicians")
- **`--output`**: output file path (default: `~/Downloads/brand_name_report.md`)
- **`--languages`**: comma-separated language codes for cross-linguistic entropy (default: `en,fr`)
- **`--skip-network`**: if present, skip network-dependent scorers (phonetic neighbors, cross-linguistic)
- **`--skip-llm`**: if present, skip parallel AI deep-dive analyses

### Phase 2: Compute Metrics

The `brand` package lives at `/Users/thorwhalen/Dropbox/py/proj/t/brand`.
Run Python from that directory with `sys.path.insert(0, '.')`.

**2a. Local/fast metrics** -- Run in a single Python script for all names:

```python
import json, sys
sys.path.insert(0, '/Users/thorwhalen/Dropbox/py/proj/t/brand')

names = [...]  # from arguments

from brand._scorers.phonetic import syllable_count, stress_pattern, sound_symbolism
from brand._scorers.linguistic import (
    novelty_score, existing_word, substring_hazards,
    spelling_transparency, pronunciation_entropy,
)
from brand._scorers.visual import letter_balance, keyboard_distance, name_length
from brand._scorers.composite import brandability_score

# Also useful sub-metrics from composite:
from brand._scorers.composite import (
    _vowel_consonant_ratio, _unique_letter_ratio,
    _has_repeating_pattern, _harsh_cluster_count, _positive_morpheme_score,
    _POSITIVE_MORPHEMES,
)

results = {}
for name in names:
    r = {}
    # Phonetic
    r['syllables'] = syllable_count(name)
    r['stress_pattern'] = stress_pattern(name)
    r['sound_symbolism'] = sound_symbolism(name)
    # Linguistic
    r['novelty'] = novelty_score(name)
    r['existing_word'] = existing_word(name)
    r['substring_hazards'] = substring_hazards(name)
    r['spelling_transparency'] = spelling_transparency(name)
    r['pronunciation_entropy_en'] = pronunciation_entropy(name, languages=('en',))
    r['pronunciation_entropy_multi'] = pronunciation_entropy(name, languages=tuple(LANGUAGES))
    # Visual
    r['letter_balance'] = letter_balance(name)
    r['keyboard_distance'] = keyboard_distance(name)
    r['name_length'] = name_length(name)
    # Composite
    r['brandability'] = brandability_score(name)
    # Sub-metrics
    r['vowel_consonant_ratio'] = round(_vowel_consonant_ratio(name), 3)
    r['unique_letter_ratio'] = round(_unique_letter_ratio(name), 3)
    r['has_repeating_pattern'] = _has_repeating_pattern(name)
    r['harsh_cluster_count'] = _harsh_cluster_count(name)
    r['positive_morpheme_score'] = round(_positive_morpheme_score(name), 3)
    r['found_morphemes'] = [m for m in _POSITIVE_MORPHEMES if m in name.lower()]
    results[name] = r

print(json.dumps(results, indent=2))
```

**2b. Network metrics** (unless `--skip-network`):

- **Cross-linguistic check**: Use `cross_linguistic_check()` but exclude `ja` (MeCab
  not installed). Fall back to per-language `zipf_frequency` with try/except.
- **Phonetic neighbors**: Use `phonetic_neighbors()` from Datamuse API.

**2c. Pronunciation entropy detail** -- Get per-grapheme breakdown for the appendix:

```python
from brand._scorers.linguistic import pronunciation_entropy_detail
for name in names:
    detail = pronunciation_entropy_detail(name, languages=tuple(LANGUAGES))
```

### Phase 3: Parallel AI Deep-Dive Analyses

Unless `--skip-llm`, launch **one Agent per name in parallel** using the
`general-purpose` subagent type. Each agent receives:

1. The company context
2. All computed metrics for that specific name
3. Instructions to produce a half-page analysis covering:
   - Etymology/morpheme roots
   - Pronunciation and sound feel
   - Visual impression
   - Domain fit (for the specific company context)
   - Grant appeal (US and EU)
   - Investor appeal
   - International considerations
   - **Arguments FOR** using the name
   - **Arguments AGAINST** using the name
4. Instruction: "Write as a cohesive half-page analysis, not just bullet points.
   Be honest and balanced. DO NOT search the web or read files."

**Agent prompt template:**

```
You are a brand naming expert. Write a detailed, half-page analysis of the
name "{NAME}" as a candidate company name for a company working on {CONTEXT}.

Here are the computed metrics for this name:
{METRICS_BLOCK}

Provide:
1. A detailed analysis covering etymology/morpheme roots, pronunciation,
   sound feel, visual impression, domain fit, grant appeal, investor appeal,
   international considerations
2. Arguments FOR using this name
3. Arguments AGAINST using this name

Write it as a cohesive half-page analysis, not just bullet points.
Be honest and balanced. DO NOT search the web or read files.
```

### Phase 4: Compile the Report

Write a markdown report to the output path with these sections:

#### Structure

```markdown
# Brand Name Deep Dive: {N} Candidates for {SHORT_CONTEXT}

## Comparative Metrics Table

{Note which metrics are identical across all candidates and omit them from the table}

{Transposed table: names as ROWS, metrics as COLUMNS -- this prevents
PDF overflow. Use abbreviated column headers with a legend below.}

**Metric explanations:**
{One-line explanation of each metric in the table}

### Visual Balance
{Table: Name | Ascenders | Descenders | Neutral | Character}

### Key Phonetic Neighbors
{Table: Name | Notable neighbors}

---

## Individual Deep-Dive Analyses
{Numbered sections, one per name, from the parallel agents}

---

## Summary Ranking by Key Differentiators
{Table: Dimension | Top Picks}
```

#### Table formatting rules

- **Transpose the main comparison table** -- names as rows, metrics as columns.
  This keeps the table narrow enough for PDF rendering.
- **Omit uniform metrics** -- If all candidates have the same value for a metric,
  mention it in a sentence above the table instead of wasting a column.
- **Bold standout values** -- Best-in-class values get `**bold**`.
- **Include metric explanations** -- A bullet list below the table explaining
  each column in one sentence.

### Phase 5: Present and Iterate

After generating the report:
1. Show the user the summary ranking table inline
2. Tell them the full report is at the output path
3. Be ready for iteration:
   - **Founder commentary**: Add a "Founder Commentary and Responses" section
     with quoted feedback and analytical responses
   - **New metrics**: If the user identifies gaps (like we did with pronunciation
     entropy), implement the metric in the brand package and re-run
   - **Table reformatting**: Transpose, split, or abbreviate as needed for
     the user's output format

## Key Lessons from Past Usage

These are patterns discovered through iteration that should be applied by default:

### Cross-linguistic vowel stability matters
Names built on **a**, **o** vowels are more pronunciation-stable across English
and French than names using **e** and **i**. The `pronunciation_entropy` scorer
with `languages=('en', 'fr')` captures this quantitatively.

### Phonetic neighbors reveal hidden brand risks
Names like "Ilumin" score well on automated metrics but have crowded phonetic
neighborhoods (Illumina) that create real trademark and confusion risks. Always
include the phonetic neighbors table and flag names that neighbor known companies
in the same industry.

### The "oh, it sounds like X" test
Founders will have gut reactions about names sounding like existing products
(dental brands, pharma prefixes, yogurt companies). These reactions are valid
and often map to phonetic neighbor data. Surface this proactively.

### PDF formatting
Tables with more than 6-7 columns will overflow in PDF. Always transpose
the main comparison table (names as rows) and use abbreviated headers.

## Dependencies

- Python 3.12+
- The `brand` package at `/Users/thorwhalen/Dropbox/py/proj/t/brand`
- `wordfreq`, `pronouncing` (installed in the brand package environment)
- Network access for Datamuse API (phonetic neighbors) and cross-linguistic checks
- Agent tool access for parallel deep-dive analyses
