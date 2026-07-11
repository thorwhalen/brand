"""Score a list of candidate names with all fast, local (no-API, no-AI) scorers
and write a CSV suitable for Google Sheets / Excel.

Usage
-----
Run on the default input (~80K DNS-verified CV3/VC3 names):

    python examples/score_all_to_csv.py

Run on your own list (one name per line):

    python examples/score_all_to_csv.py --input ~/Downloads/my_names.txt --output ~/Downloads/my_scores.csv

Notes
-----
- Input format: plain text, one candidate name per line. Blank lines ignored.
- All scorers are formulaic / local. No network calls, no LLMs.
- Throughput: ~10,000 names/second on a 2024 Mac.
- The epitran library is silenced because it would otherwise log a per-call
  warning to stderr — at 80K names that I/O alone made the script appear to hang.
"""

import argparse
import csv
import logging
import sys
import time
import warnings
from pathlib import Path

# Silence epitran's per-call "lex_lookup (from flite) is not installed" warning.
logging.getLogger("epitran").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

_PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ_ROOT))

from brand._scorers.linguistic import (
    novelty_score,
    existing_word,
    spelling_transparency,
    pronunciation_entropy,
)
from brand._scorers.visual import keyboard_distance
from brand._scorers.composite import (
    brandability_score,
    _vowel_consonant_ratio,
    _unique_letter_ratio,
    _has_repeating_pattern,
    _harsh_cluster_count,
    _positive_morpheme_score,
)


DEFAULT_INPUT = _PROJ_ROOT / "misc" / "dns_verified_cv3_and_vc3.txt"
DEFAULT_OUTPUT = Path.home() / "Downloads" / "brand_scores_cv3_vc3.csv"


COLUMNS = [
    "name",
    "vowel_consonant_ratio",
    "unique_letter_ratio",
    "has_repeating_pattern",
    "harsh_cluster_count",
    "keyboard_distance",
    "novelty_score",
    "existing_word",
    "spelling_transparency",
    "pronunciation_entropy_en",
    "pronunciation_entropy_en_fr",
    "brandability_score",
    "positive_morpheme_score",
]


def _safe(fn, *args, default=None, **kw):
    try:
        return fn(*args, **kw)
    except Exception:
        return default


def score_name(name: str) -> dict:
    """Compute all CSV columns for a single name."""
    return {
        "name": name,
        "vowel_consonant_ratio": round(_safe(_vowel_consonant_ratio, name, default=0.0), 4),
        "unique_letter_ratio": round(_safe(_unique_letter_ratio, name, default=0.0), 4),
        "has_repeating_pattern": _safe(_has_repeating_pattern, name),
        "harsh_cluster_count": _safe(_harsh_cluster_count, name),
        "keyboard_distance": round(_safe(keyboard_distance, name, default=0.0), 4),
        "novelty_score": round(_safe(novelty_score, name, default=0.0), 4),
        "existing_word": _safe(existing_word, name),
        "spelling_transparency": round(_safe(spelling_transparency, name, default=0.0), 4),
        "pronunciation_entropy_en": round(
            _safe(pronunciation_entropy, name, languages=("en",), default=0.0), 4
        ),
        "pronunciation_entropy_en_fr": round(
            _safe(pronunciation_entropy, name, languages=("en", "fr"), default=0.0), 4
        ),
        "brandability_score": round(_safe(brandability_score, name, default=0.0), 4),
        "positive_morpheme_score": round(_safe(_positive_morpheme_score, name, default=0.0), 4),
    }


def score_names_to_csv(
    names,
    output_path: Path,
    *,
    progress_every: int = 10000,
):
    """Score an iterable of names and stream rows to a CSV file."""
    output_path = Path(output_path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    names = list(names)
    n_total = len(names)
    print(f"Writing {n_total} rows to {output_path}", flush=True)

    t0 = time.time()
    with open(output_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for i, name in enumerate(names, 1):
            writer.writerow(score_name(name))
            if progress_every and i % progress_every == 0:
                elapsed = time.time() - t0
                rate = i / elapsed
                eta = (n_total - i) / rate if rate else 0
                print(
                    f"  {i}/{n_total} ({i*100//n_total}%) "
                    f"— {rate:.0f}/s, ETA {eta:.0f}s",
                    flush=True,
                )

    elapsed = time.time() - t0
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(
        f"Done in {elapsed:.1f}s ({n_total/elapsed:.0f} names/s) — "
        f"{output_path} ({size_mb:.1f} MB)",
        flush=True,
    )
    return output_path


def load_names(input_path: Path) -> list[str]:
    """Load one-name-per-line from a text file."""
    with open(Path(input_path).expanduser()) as fh:
        return [line.strip() for line in fh if line.strip()]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Score candidate brand names with all fast local scorers and "
            "write a CSV. Input is one name per line."
        ),
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input file, one name per line (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    names = load_names(args.input)
    print(f"Loaded {len(names)} names from {args.input}", flush=True)
    score_names_to_csv(names, args.output)


if __name__ == "__main__":
    main()
