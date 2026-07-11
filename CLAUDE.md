# brand — project notes for Claude Code

## Bulk-scoring names to CSV

To score a list of candidate names with all the fast local scorers (no
network, no LLM) and write a CSV for spreadsheet analysis, use the existing
script — do not re-implement:

```bash
python examples/score_all_to_csv.py \
    --input  ~/path/to/names.txt \
    --output ~/Downloads/scores.csv
```

- Input: plain text, one name per line
- Throughput: ~10,000 names/sec; 80K names finishes in ~7 seconds
- 13 columns: `name`, `vowel_consonant_ratio`, `unique_letter_ratio`,
  `has_repeating_pattern`, `harsh_cluster_count`, `keyboard_distance`,
  `novelty_score`, `existing_word`, `spelling_transparency`,
  `pronunciation_entropy_en`, `pronunciation_entropy_en_fr`,
  `brandability_score`, `positive_morpheme_score`
- The script silences `epitran`'s per-call "lex_lookup (from flite) is not
  installed" warning. Without that, stderr I/O alone makes a 7-second job
  take over an hour. Don't remove the suppression.

Defaults (no flags) score `misc/dns_verified_cv3_and_vc3.txt` to
`~/Downloads/brand_scores_cv3_vc3.csv`.

## Pre-computed name pools

`misc/dns_verified_cv3_and_vc3.txt` and `misc/available_*.txt` are DNS- and
WHOIS-verified `.com`-available 6-letter names (CVCVCV / VCVCVC patterns),
last refreshed 2026-03-28. Reuse these instead of regenerating.

## Cached pipeline runs

Persisted scoring/WHOIS/OpenCorporates/LLM-rating runs live at
`~/.config/brand/pipelines/`. The `research_company_2026` project there
contains the full funnel from 79K candidates → top 100 used for the
"AI Health-Tech" report. Re-rank for a new company by re-running just the
LLM stage with a new `--context`.

## Comparative report skill

For a side-by-side deep-dive report on a small shortlist (5–15 names), use
the `brand-name-report` skill (global) — it computes per-name metrics and
launches parallel agents for qualitative analysis.
