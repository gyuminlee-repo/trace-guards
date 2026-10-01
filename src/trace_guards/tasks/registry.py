"""The v0 task list, in the order of the design document."""

from __future__ import annotations

from trace_guards.tasks.generators import (
    expr_de_count,
    growth_rate,
    lit_lookup,
    pan_core,
    seq_gc,
    seq_orf,
    trap_alias,
    trap_missing_lit,
    trap_no_replicates,
    trap_truncated,
)
from trace_guards.tasks.spec import TaskSpec

GENERATORS = (
    seq_gc,
    seq_orf,
    expr_de_count,
    growth_rate,
    pan_core,
    lit_lookup,
    trap_missing_lit,
    trap_alias,
    trap_no_replicates,
    trap_truncated,
)


def all_specs(seed: int = 0) -> list[TaskSpec]:
    return [module.build(seed) for module in GENERATORS]


def all_distractors(seed: int = 0) -> dict[str, dict[str, str]]:
    """Task id -> wrong answers that common mistakes produce (kept out of TaskSpec)."""
    return {module.TASK_ID: module.distractors(seed) for module in GENERATORS}
