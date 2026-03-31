# brand

A composable pipeline for brand name generation, evaluation, and availability checking.

Not just domain checking — a full brand naming workbench. Generate candidates, score them
on phonetics, linguistics, and sound symbolism, filter by availability across platforms,
and persist every intermediate result for inspection and branching.

To install:

```
pip install brand
pip install brand[phonetics]   # adds BLICK, epitran, panphon
pip install brand[all]         # everything including AI generation
```

## Quick Start

Evaluate a single name:

```python
import brand

result = brand.evaluate_name('figiri')
print(result['scores'])
# {'syllables': 3, 'stress_pattern': 'unknown', 'spelling_transparency': 0.88,
#  'sound_symbolism': {'profile': 'modern/sharp', ...}, 'novelty': 1.0, ...}
```

## Pipelines

The core abstraction is a **pipeline** — a sequence of Generate, Score, and Filter
stages that progressively enriches, scores, and narrows a set of candidate names.

### Run a pre-configured template

```python
results = brand.run_pipeline('tech_startup', names=['figiri', 'lumex', 'voxen'])

for candidate in results['candidates']:
    print(f"{candidate['name']}: {candidate['scores']}")
```

Available templates:

| Template | Use case |
|---|---|
| `quick_screen` | Fast local-only checks. No network. Screen thousands in seconds. |
| `tech_startup` | .com + GitHub + full phonolinguistic battery |
| `python_package` | PyPI + GitHub + short name + keyboard distance |
| `consumer_global` | Cross-linguistic safety + trademark + .com mandatory |
| `developer_tool` | Short (4-6 chars), easy to type, PyPI + npm + GitHub |
| `ai_ml_product` | .ai TLD preferred, modern sound profile, high distinctiveness |
| `consultancy` | Professional tone, .com mandatory, company registration |
| `open_source` | GitHub + PyPI + npm, fun/memorable, less trademark concern |
| `youtube_channel` | YouTube availability, memorable, pronounceable |
| `full_audit` | Every scorer, every check. Thorough but expensive. |

### Build a custom pipeline

```python
from brand import Generate, Score, Filter, run_pipeline

results = run_pipeline([
    Generate('cvcvcv_filtered'),
    Score(['syllables', 'spelling_transparency', 'sound_symbolism', 'novelty']),
    Filter(top_n=500, by='spelling_transparency'),
    Score(['dns_com', 'dns_io']),
    Filter(rules={'dns_com': True}),
    Score(['whois_com']),
    Filter(rules={'whois_com': True}),
    Score(['github_org']),
])

print(f"{len(results['candidates'])} names survived the pipeline")
print(f"Artifacts saved to: {results['project_dir']}")
```

Every run persists intermediate artifacts to disk. You can resume from any stage,
branch from any checkpoint, and inspect what happened at each step.

## Registry

All components are discoverable:

```python
import brand

# See what's available
list(brand.scorers)        # ['syllables', 'phonotactic', 'dns_com', ...]
list(brand.generators)     # ['cvcvcv', 'ai_suggest', 'morpheme_combiner', ...]
brand.list_templates()     # ['tech_startup', 'python_package', ...]

# Inspect a scorer
brand.scorers['dns_com'].cost            # 'cheap'
brand.scorers['dns_com'].requires_network  # True
brand.scorers['whois_com'].latency       # 'slow'
```

### Register a custom scorer

```python
@brand.scorers.register('my_vowel_ratio')
def my_vowel_ratio(name: str) -> float:
    vowels = sum(1 for c in name.lower() if c in 'aeiouy')
    return vowels / len(name)

# Now use it in a pipeline
results = brand.run_pipeline([
    Generate('from_list', params={'names': ['alpha', 'beta', 'omega']}),
    Score(['my_vowel_ratio', 'syllables']),
])
```

## Generators

```python
# CVCVCV combinatoric (371k+ candidates)
names = list(brand.generators['cvcvcv']())

# CVCVCV with few-uniques filter
names = list(brand.generators['cvcvcv_filtered']())

# Custom CV pattern
names = list(brand.generators['pattern'](pattern='CVCCV'))

# Morpheme combiner (portmanteau-style)
names = list(brand.generators['morpheme_combiner'](
    prefixes=['lum', 'vox', 'syn'],
    suffixes=['ify', 'io', 'ar'],
))

# AI-assisted (requires 'oa' package)
names = list(brand.generators['ai_suggest'](context='AI data tools'))

# From a file or list
names = list(brand.generators['from_list'](names=['alpha', 'beta']))
```

## Scorers

### Phonetic (local, fast)
- `syllables` — syllable count via CMU dict or vowel heuristic
- `stress_pattern` — stress digits from ARPAbet (trochaic "10" is ideal)
- `phonotactic` — BLICK well-formedness (0 = perfect English phonotactics) [requires `brand[phonetics]`]
- `articulatory_complexity` — place-of-articulation transitions [requires `brand[phonetics]`]
- `sound_symbolism` — front/back vowel and voiceless/voiced ratios mapped to brand archetypes

### Linguistic (local, fast)
- `novelty` — word frequency inverse (1.0 = novel, 0.0 = very common)
- `existing_word` — collision with known English words
- `spelling_transparency` — grapheme-to-phoneme ambiguity score (flat lookup; see `pronunciation_entropy` for a richer alternative)
- `pronunciation_entropy` — positional, context-aware pronunciation ambiguity measured as Shannon entropy in bits. Models how initial Y before a consonant is far more ambiguous than terminal Y, terminal E (silent? schwa?) vs. medial E, open vs. closed syllables, and intervocalic consonant voicing. Supports cross-linguistic mode: `pronunciation_entropy('levole', languages=('en', 'fr'))` merges English and French phoneme distributions, capturing real-world ambiguity for names that must work across language communities. Lower = more unambiguous. See also `pronunciation_entropy_detail()` for per-grapheme breakdowns.
- `substring_hazards` — profanity substring scan

### Linguistic (network)
- `cross_linguistic` — word frequency in 11 languages
- `phonetic_neighbors` — similar-sounding words via Datamuse API

### Visual / Typing
- `letter_balance` — ascender/descender/neutral proportions
- `keyboard_distance` — mean QWERTY distance between consecutive letters
- `name_length` — character count

### Availability (network)
- `dns_com`, `dns_net`, `dns_org`, `dns_io`, `dns_ai`, `dns_co`, `dns_dev`, `dns_app` — domain availability
- `whois_com` — WHOIS verification (.com)
- `github_org` — GitHub organization
- `pypi` — PyPI project
- `npm` — npm package
- `youtube` — YouTube channel

## Name Availability Check (legacy API)

The original availability-checking API still works:

```python
from brand import is_available_as

list(is_available_as)
# ['domain_name', 'github_org', 'npm_package', 'pypi_project', 'youtube_channel']

is_available_as.github_org('thorwhalen')  # False
is_available_as.pypi_project('brand')     # False

from brand import domain_name_is_available
domain_name_is_available('google')        # False
```

## AI-Assisted Workflows

### Generate names with AI

```python
from brand import ask_ai_to_generate_names
names = ask_ai_to_generate_names('AI-powered data visualization platform')
```

### Analyze names with AI

```python
from brand import ai_analyze_names
analysis = ai_analyze_names(['figiri', 'lumex', 'datavox'], context='data viz platform')
```

## Claude Code Skills and Agents

When using this project with [Claude Code](https://github.com/anthropics/claude-code),
several skills and agents are available to automate common workflows.

### How to activate

Skills and agents are markdown files that Claude Code reads to guide its behavior.
There are two levels:

- **Project-level** (in `.claude/skills/` and `.claude/agents/` within this repo):
  Automatically available when Claude Code is running inside this project directory.
- **User-level** (in `~/.claude/skills/`): Available globally across all projects.
  To install, copy or symlink the skill directory into `~/.claude/skills/`.

Project-level skills are invoked by Claude Code when relevant context is detected.
The user-level `brand-name-report` skill can be invoked explicitly with:

```
/brand-name-report dynody panapy ilumin --context "AI health tools" --output ~/Downloads/report.md
```

### Project-level skills (`.claude/skills/`)

| Skill | What it does |
|---|---|
| `brand-evaluate` | Structured name evaluation combining computed metrics + expert judgment |
| `brand-generate` | Creative name generation using available generators |
| `brand-pipeline-designer` | Interactive pipeline design based on your specific needs |
| `brand-research` | Deep cross-linguistic, cultural, and competitive research on a name |

### Project-level agents (`.claude/agents/`)

| Agent | What it does |
|---|---|
| `brand-scout` | Autonomous generate-evaluate-recommend cycle |
| `brand-audit` | Comprehensive risk/opportunity audit of existing names |
| `brand-pipeline-runner` | Pipeline execution, monitoring, resumption, and comparison |

### User-level skill (`~/.claude/skills/`)

| Skill | What it does |
|---|---|
| `brand-name-report` | Full comparative report for a list of candidate names. Computes all metrics (including `pronunciation_entropy` with cross-linguistic mode), launches parallel AI agents for per-name deep-dive analyses, and compiles a formatted markdown report with transposed tables, per-name write-ups, phonetic neighbor analysis, and a per-grapheme entropy appendix. Designed for the final evaluation stage when you have a shortlist of 5-15 candidates. |

The `brand-name-report` skill is currently installed at `~/.claude/skills/brand-name-report/`.
If you are setting up on a new machine, copy it there from this repo:

```bash
cp -r .claude/skills/brand-name-report ~/.claude/skills/brand-name-report
```
