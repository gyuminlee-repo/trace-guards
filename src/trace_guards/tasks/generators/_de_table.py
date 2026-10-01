"""Synthetic differential expression table shared by expr_de_count and trap_truncated."""

from __future__ import annotations

import math
import random

FILE = "de_results.tsv"
HEADER = ("gene", "baseMean", "log2FoldChange", "lfcSE", "pvalue", "padj")

# Categories that satisfy "padj < 0.05 and |log2FoldChange| >= 1".
HIT_CATEGORIES = ("hit_up", "hit_down", "boundary_up", "boundary_down")

QUESTION = (
    f"The file `{FILE}` is a differential expression table with one row per gene. "
    "Count the genes whose adjusted p-value (column `padj`) is below 0.05 and whose "
    "absolute log2 fold change (column `log2FoldChange`) is at least 1. A gene with "
    "a missing `padj` does not count. Report the count as an integer. "
)


def _log_uniform(rng: random.Random, low: float, high: float) -> float:
    return math.exp(rng.uniform(math.log(low), math.log(high)))


def _row(rng: random.Random, category: str) -> list[str]:
    """Numeric fields of one row. Ranges keep every value clear of the thresholds."""
    large = rng.uniform(1.05, 4.0)
    small = rng.uniform(0.02, 0.95)
    sign = rng.choice((1, -1))
    significant_padj = _log_uniform(rng, 1e-8, 0.04)
    if category == "hit_up":
        lfc, padj = large, significant_padj
    elif category == "hit_down":
        lfc, padj = -large, significant_padj
    elif category == "boundary_up":
        lfc, padj = 1.0, significant_padj
    elif category == "boundary_down":
        lfc, padj = -1.0, significant_padj
    elif category == "small_effect":
        lfc, padj = sign * small, significant_padj
    elif category == "raw_only":
        lfc, padj = sign * large, rng.uniform(0.06, 0.4)
    elif category == "na_padj":
        lfc, padj = sign * large, None
    elif category == "null":
        lfc, padj = sign * rng.choice((large, small)), rng.uniform(0.2, 0.99)
    else:
        raise ValueError(f"unknown category {category!r}")

    if category == "raw_only":
        pvalue = rng.uniform(0.001, 0.04)
    elif category == "na_padj":
        pvalue = _log_uniform(rng, 1e-4, 0.04)
    else:
        pvalue = padj * rng.uniform(0.1, 0.9)
        if category == "null":
            pvalue = max(pvalue, 0.06)
    return [
        f"{_log_uniform(rng, 5, 5000):.1f}",
        f"{lfc:.3f}",
        f"{rng.uniform(0.1, 0.5):.3f}",
        f"{pvalue:.3g}",
        "NA" if padj is None else f"{padj:.3g}",
    ]


def make_rows(rng: random.Random, counts: dict[str, int]) -> list[tuple[str, list[str]]]:
    """Shuffled (category, fields) rows; gene names follow the shuffled order."""
    categories = [category for category, n in counts.items() for _ in range(n)]
    rng.shuffle(categories)
    return [
        (category, [f"gene_{i:04d}", *_row(rng, category)])
        for i, category in enumerate(categories, start=1)
    ]


def random_counts(rng: random.Random) -> dict[str, int]:
    return {
        "hit_up": rng.randint(8, 14),
        "hit_down": rng.randint(6, 12),
        "boundary_up": rng.randint(1, 2),
        "boundary_down": rng.randint(1, 2),
        "small_effect": rng.randint(6, 10),
        "raw_only": rng.randint(5, 9),
        "na_padj": rng.randint(4, 8),
        "null": rng.randint(55, 70),
    }
