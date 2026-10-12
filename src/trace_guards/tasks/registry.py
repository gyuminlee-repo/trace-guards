"""The v0 task list, in the order of the design document."""

from __future__ import annotations

import json
from pathlib import Path

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

V1_TASK_DIR = Path(__file__).with_name("data")


def fixed_specs(suite: str, seed: int = 0) -> list[TaskSpec]:
    if suite not in ("v1_holdout", "v1_control") or seed != 0:
        raise ValueError("fixed v1 suites require a known suite and seed zero")
    rows = json.loads((V1_TASK_DIR / f"{suite}.json").read_text(encoding="utf-8"))
    specs = [TaskSpec(**(row | {"tools": tuple(row["tools"])})) for row in rows]
    if not specs or len({s.id for s in specs}) != len(specs):
        raise ValueError("fixed suite must contain unique nonempty task ids")
    return specs


def all_specs(seed: int = 0) -> list[TaskSpec]:
    return [module.build(seed) for module in GENERATORS]


def all_distractors(seed: int = 0) -> dict[str, dict[str, str]]:
    """Task id -> wrong answers that common mistakes produce (kept out of TaskSpec)."""
    return {module.TASK_ID: module.distractors(seed) for module in GENERATORS}
