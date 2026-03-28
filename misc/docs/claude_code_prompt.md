# Task: Redesign the `brand` package with a pipeline-based architecture, pluggable components, Claude skills, and agents

## Context

You are working on the `brand` Python package (`pip install brand`, repo at `github.com/thorwhalen/brand`). It currently handles domain name generation and availability checking. We want to evolve it into a comprehensive **brand name evaluation and generation system** built around a **composable pipeline architecture** with pluggable components, persistent intermediate artifacts, and pre-configured pipeline templates.

## Reference Documents — Read These First

Before designing anything, read these two documents carefully:

1. **`misc/docs/brand_naming_deep_research.md`** — A comprehensive research report covering Python libraries (G2P, phonotactics, feature vectors, word frequency), APIs (Datamuse, Wiktionary, USPTO, OpenCorporates), academic literature on sound symbolism in branding (Klink, Yorkston & Menon, Motoki et al.), branding books (Watkins, Meyerson), cross-linguistic safety resources, and profanity databases. This is your library/tool reference.

2. **`misc/docs/brand_naming_skill_prompt.md`** — A detailed skill prompt describing the four-tier evaluation pipeline (phonolinguistic metrics → lexical/semantic checks → availability → expert synthesis), output formats, scoring weights, and the specific computations each tier requires. This is your evaluation logic reference.

These documents contain the *what* and the *why*. Your job is the *how* — the architecture, the code, the skills, and the agents.

## Core Architectural Concept: The Pipeline

The central abstraction is a **pipeline** — a sequence of stages that takes a stream of candidate names and progressively enriches, scores, filters, and narrows them. Think of it like a data processing pipeline (or a Unix pipeline, or a DAG), but for brand names.

A pipeline is a sequence of **stages**. Each stage is one of:

### Stage Types

1. **Generate** — Produces candidate names. This is always the first stage (or the input is a pre-existing list). Examples:
   - CVCVCV combinatoric generator (already exists)
   - AI-assisted generator (already exists)
   - Morpheme combiner
   - Sound-symbolism-targeted generator
   - Load from file / list

2. **Score** — Takes a batch of names, computes one or more metrics on each, and attaches the results. Multiple scorers can run in a single stage (parallel stats). Each scorer is a function `(name: str, **kwargs) -> float | bool | dict`. A scoring stage takes a list of scorer specs and produces a dict of results per name. Examples:
   - Phonotactic well-formedness (BLICK score)
   - Syllable count
   - Stress pattern
   - Articulatory complexity
   - Sound symbolism profile
   - Spelling transparency
   - Novelty (wordfreq)
   - Letter balance / visual score
   - Keyboard distance
   - DNS check (quick, returns bool)
   - WHOIS check (slower, returns bool)
   - Domain availability (.com, .ai, .io, .net, etc.)
   - GitHub org available
   - PyPI available
   - npm available
   - YouTube channel available
   - Cross-linguistic safety (substring against profanity lists)
   - Phonetic neighbor count (Datamuse sounds-like)
   - Trademark search (USPTO)
   - Company name collision (OpenCorporates)

   Note: availability checks are also scorers — they return a bool (or a float: 1.0/0.0). This unifies the interface. However, scorers should be tagged with metadata like `cost` (cheap/expensive), `requires_network` (bool), `latency` (fast/slow), and `parallelizable` (bool) so the pipeline can make smart scheduling decisions.

3. **Filter** — Takes the scored batch and reduces it based on a rule. A filter is a predicate on the accumulated scores. Examples:
   - Keep top N by aggregate score
   - Keep top N% by a specific scorer
   - Keep only names where `dot_com_available == True`
   - Keep only names where `blick_score < 5`
   - Keep only names where `dot_com_available or dot_net_available`
   - Keep only names with no cross-linguistic flags
   - Custom predicate function

### Pipeline Definition

A pipeline is a list of stages, specified declaratively. Something like:

```python
pipeline = [
    Generate("cvcvcv", consonants="bdfglmnprstvz", vowels="aeiouy", filt=few_uniques),
    Score(["phonotactic", "syllables", "stress", "articulatory_complexity", "sound_symbolism"]),
    Filter(top_n=1000, by="aggregate"),
    Score(["dns_com", "dns_net"]),  # quick DNS check, parallelizable
    Filter(lambda r: r["dns_com"] or r["dns_net"]),
    Score(["whois_com"]),  # slower, confirms DNS results
    Filter(lambda r: r["whois_com"]),
    Score(["company_name_available"]),
    Filter(lambda r: r["company_name_available"]),
]
```

The exact API is yours to design. The above is just to convey the intent — **don't cargo-cult this syntax**. Think about what makes the cleanest, most composable, most Pythonic API. Consider:
- Should stages be plain dicts/tuples (maximally serializable) or objects?
- Should the pipeline be a list, or should it use a builder pattern?
- Should `Score` and `Filter` be separate, or should there be a `ScoreAndFilter` combo for the common case?
- How does the user specify scorer parameters (e.g., which TLDs to check, which languages for cross-linguistic safety)?
- How does a custom predicate get serialized if we want to persist pipeline definitions?

### Pipeline Persistence and Artifacts

Every pipeline run creates a **project folder** with all intermediate artifacts. Default location: `~/.local/share/brand/pipelines/{project_name}_{timestamp}/` (configurable via env var `BRAND_PIPELINES_DIR` or a `.env` / config file).

The project folder should contain:
- `pipeline.json` (or `.yaml`) — The pipeline definition (serialized, so it can be re-run or branched)
- `stage_00_generate/names.json` — The generated candidates
- `stage_01_score/results.json` — Names + computed scores after first scoring stage
- `stage_02_filter/results.json` — Filtered subset
- `stage_03_score/results.json` — Names + additional scores
- ... and so on for each stage
- `final/results.json` — The final output

This means:
- You can **resume** a pipeline from any stage (if stage 2 failed, fix and re-run from stage 2 without regenerating)
- You can **branch** from any stage (take the stage_02 results and run a different filtering/scoring path)
- You can **inspect** what happened at each stage (how many candidates survived each filter, what scores looked like)
- Intermediate artifacts use a storage-agnostic interface (could be files, could be a `dol` store — use your judgment, but files-on-disk is the default)

### Pipeline Templates (Pre-configured Pipelines)

Create 8-10 pre-configured pipeline templates for common use cases. Each template knows what it's optimizing for and what availability checks matter. Store these in `brand/pipelines/templates/` or similar.

Think about use cases like:

- **Tech startup (general)** — Needs .com, GitHub org, flexible name, modern sound profile. Full phonolinguistic + availability battery.
- **Python package** — Needs PyPI availability, short name, easy to type. Keyboard distance matters. .com less critical.
- **Consumer brand (global)** — Heavy cross-linguistic safety checking, trademark search, .com mandatory, sound symbolism tuned for warmth/trust.
- **Developer tool / CLI** — Short (4-6 chars), easy to type, no profanity substrings, PyPI + npm + GitHub. Sound profile: sharp/precise.
- **AI/ML product** — .ai TLD preferred, modern/technical sound profile, distinctiveness high priority.
- **Consultancy / agency** — Professional tone, .com mandatory, company name registration check, trademark clear.
- **Open source project** — GitHub org, PyPI, npm. Fun/memorable over professional. Less trademark concern.
- **YouTube channel / content brand** — YouTube availability, memorable, pronounceable (will be said aloud), .com nice-to-have.
- **Full audit** — The everything pipeline. All scorers, all checks. Expensive but thorough.
- **Quick screen** — Fast, local-only checks (no network). Phonotactics + novelty + substring safety + syllables. For rapidly screening thousands of candidates.

Each template should be a serialized pipeline definition that can be loaded, inspected, and modified before running. There should also be a **default pipeline** that's used when the user just calls `evaluate_name("foo")` without specifying a pipeline. The default should be configurable via env var `BRAND_DEFAULT_PIPELINE` or a `.env` / config file.

## Component Registry

All scorers, generators, and filters should be **registered in a discoverable registry**. The user should be able to:

```python
import brand

# See what's available
list(brand.scorers)        # ['phonotactic', 'syllables', 'dns_com', 'whois_com', ...]
list(brand.generators)     # ['cvcvcv', 'ai_suggest', ...]
list(brand.filters)        # ['top_n', 'threshold', 'predicate', ...]
list(brand.pipelines)      # ['tech_startup', 'python_package', 'consumer_global', ...]

# Get metadata about a scorer
brand.scorers['phonotactic'].cost          # 'cheap'
brand.scorers['phonotactic'].requires_network  # False
brand.scorers['whois_com'].cost            # 'expensive'
brand.scorers['whois_com'].requires_network    # True

# Register a custom scorer
@brand.scorers.register('my_custom_scorer')
def my_custom_scorer(name: str) -> float:
    return len(name) / 10  # silly example

# Run a pre-configured pipeline
results = brand.run_pipeline('tech_startup', context="AI-powered data visualization")

# Run a custom pipeline
results = brand.run_pipeline([
    brand.Generate("cvcvcv"),
    brand.Score(["phonotactic", "syllables", "my_custom_scorer"]),
    brand.Filter(top_n=100),
])
```

Again — don't cargo-cult this exact API. Design what's cleanest. The point is: discoverable, extensible, composable.

## Dependencies

Add new libraries to `pyproject.toml` (migrate from `setup.cfg` while you're at it). Use optional dependency groups:

- **Core**: `pronouncing`, `wordfreq`, `requests` (already a dep), `dol` (already a dep)
- **`[phonetics]`**: `epitran`, `panphon`, `python-BLICK`
- **`[all]`**: everything

Scorers that need optional deps should fail gracefully with an informative error ("This scorer requires the `phonetics` extra. Install with: `pip install brand[phonetics]`").

## Claude Skills (`.claude/skills/`)

### `.claude/skills/brand-evaluate.md`
The main evaluation skill. Adapted from `misc/docs/brand_naming_skill_prompt.md` but formatted as a Claude Code skill. Instructs the agent to use the `brand` package's Python tools and follow the four-tier pipeline.

### `.claude/skills/brand-generate.md`
Focused on name generation — use generators, apply quick filters, present shortlists.

### `.claude/skills/brand-pipeline-designer.md`
**This is important.** A skill that helps the user *design* a custom pipeline interactively. The agent should:
- Ask what the name is for (company, product, package, channel, etc.)
- Ask about target audience and market (global? English-only? Technical?)
- Ask about must-have availability (which domains, which platforms)
- Ask about tone/brand archetype (modern, warm, professional, playful)
- Ask about budget for the search (quick screen vs. full audit)
- Based on answers, assemble a pipeline definition from the available components
- Show the user the assembled pipeline, explain what each stage does and why
- Offer to modify before running
- Optionally suggest a similar pre-configured template as a starting point
- Save the pipeline definition so it can be reused

### `.claude/skills/brand-research.md`
Deep research on a specific name — cross-linguistic deep-dive, competitive landscape, trademark risk, cultural associations.

Create additional skills if they earn their place.

## Claude Agents (`.claude/agents/`)

### `.claude/agents/brand-scout.md`
Runs a full generate → evaluate → recommend cycle. Takes context, picks or assembles an appropriate pipeline, runs it, presents top candidates with full scorecards.

### `.claude/agents/brand-audit.md`
Audits existing names. Takes one or more names + context, runs the full evaluation pipeline, identifies risks/opportunities, suggests alternatives.

### `.claude/agents/brand-pipeline-runner.md`
An agent specialized in running and monitoring pipelines. Can resume from checkpoints, branch from intermediate stages, compare results across pipeline variants.

Create additional agents if they earn their place.

## README Rewrite

Rewrite `README.md` to reflect the new architecture:

- Lead with the value proposition: not just domain checking, but a full brand naming workbench
- Show the simple case: `brand.evaluate_name("figiri")` → scorecard
- Show pipeline usage: pick a template, run it, get results
- Show the registry: list available scorers, register custom ones
- Show pipeline design: declarative specification, persistence, branching
- Show pre-configured templates with brief descriptions of each use case
- Installation variants: `pip install brand`, `pip install brand[phonetics]`, `pip install brand[all]`
- Mention Claude skills and agents for AI-assisted workflows
- Keep backward-compatible examples but frame them as components of the bigger system

## Coding Conventions

- Type hints, docstrings with examples, doctests where natural
- `dol`/Mapping patterns for stores (pipeline artifacts, registries)
- `argh` for CLI entry points
- `config2py` for configuration (API keys, default pipeline, pipeline storage dir)
- Informative errors over silent failures
- Functions as primary interface, classes only when earned
- Pure scoring functions (no side effects, deterministic) clearly separated from network-dependent checks
- Scorers should be tagged with metadata (cost, latency, requires_network, parallelizable)
- Pipeline persistence format should be human-readable (JSON or YAML) and round-trippable

## Process

1. **Read** the two reference documents thoroughly
2. **Design** the architecture — write out the component interfaces, registry mechanism, pipeline abstraction, stage types, persistence model, and template format before coding. Think about how stages compose, how filters reference accumulated scores, how the pipeline serializes, and how resume/branching works.
3. **Implement** in order: registry → individual scorers/generators → pipeline engine → persistence/checkpointing → facade → templates
4. **Create** the 8-10 pipeline templates
5. **Create** the Claude skills and agents
6. **Update** pyproject.toml
7. **Rewrite** README
8. **Test** — verify that at least two templates produce sensible, different results on the same seed name set. Verify that persistence/resume works. Verify that a custom scorer can be registered and used in a pipeline.

Think carefully before coding. The pipeline abstraction is the heart of the system — get it right and everything else follows naturally.
