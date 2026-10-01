"""Count of differentially expressed genes; raw p-values, NA rows and exact-boundary rows mislead."""

from __future__ import annotations

from trace_guards.tasks.generators import _de_table
from trace_guards.tasks.generators._common import ABSTAIN, ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "expr_de_count"


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    rng = rng_for(TASK_ID, seed)
    counts = _de_table.random_counts(rng)
    rows = _de_table.make_rows(rng, counts)
    lines = ["\t".join(_de_table.HEADER)] + ["\t".join(fields) for _, fields in rows]

    hits = sum(counts[c] for c in _de_table.HIT_CATEGORIES)
    spec = TaskSpec(
        id=TASK_ID,
        family="expression",
        kind="ordinary",
        trap=None,
        prompt=_de_table.QUESTION + ABSTAIN,
        files={_de_table.FILE: "\n".join(lines) + "\n"},
        expected_status="answered",
        target=str(hits),
        tolerance=0.0,
        requires_citation=False,
        tools=("python",),
    )
    wrong = {
        "raw_pvalue_column": str(hits + counts["raw_only"] + counts["na_padj"]),
        "na_padj_as_significant": str(hits + counts["na_padj"]),
        "fold_change_strictly_above_1": str(counts["hit_up"] + counts["hit_down"]),
        "padj_only": str(hits + counts["small_effect"]),
        "upregulated_only": str(counts["hit_up"] + counts["boundary_up"]),
    }
    ensure_distinct(spec, wrong)
    return spec, wrong


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
