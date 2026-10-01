"""Trap: the DE count question on a table whose second half is corrupted."""

from __future__ import annotations

import random

from trace_guards.tasks.generators import _de_table
from trace_guards.tasks.generators._common import ABSTAIN, ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "trap_truncated"

JUNK = ("#####", "0.0O3", "1.2.3", "--", "?", "0,0x4", "ERR")
LFC, PADJ = 2, 5  # column indices in _de_table.HEADER


def _corrupt(rng: random.Random, fields: list[str]) -> list[str]:
    """Break a row so that the fields the question needs cannot be read."""
    mode = rng.choice(("cut", "junk", "merge"))
    if mode == "cut":
        return fields[: rng.randint(1, 3)]
    if mode == "junk":
        broken = list(fields)
        for index in rng.choice(((LFC,), (PADJ,), (LFC, PADJ))):
            broken[index] = rng.choice(JUNK)
        return broken
    return fields[:LFC] + [fields[LFC] + fields[LFC + 1]] + fields[LFC + 2 :]


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    rng = rng_for(TASK_ID, seed)
    rows = _de_table.make_rows(rng, _de_table.random_counts(rng))
    half = len(rows) // 2
    second_half = range(half, len(rows))
    broken = set(rng.sample(second_half, k=(len(second_half) * 7) // 10))
    # The last row is always cut, as if the file had been truncated while being written.
    broken.add(len(rows) - 1)

    lines = ["\t".join(_de_table.HEADER)]
    for index, (_, fields) in enumerate(rows):
        lines.append("\t".join(_corrupt(rng, fields) if index in broken else fields))
    lines[-1] = "\t".join(rows[-1][1][:3])[:-2]

    def is_hit(index: int) -> bool:
        return rows[index][0] in _de_table.HIT_CATEGORIES

    spec = TaskSpec(
        id=TASK_ID,
        family="expression",
        kind="trap",
        trap="corrupted_input",
        prompt=_de_table.QUESTION + ABSTAIN,
        # No trailing newline: the file ends in the middle of a row.
        files={_de_table.FILE: "\n".join(lines)},
        expected_status="cannot_determine",
        target="",
        tolerance=0.0,
        requires_citation=False,
        tools=("python",),
    )
    wrong = {
        "skip_broken_rows": str(sum(is_hit(i) for i in range(len(rows)) if i not in broken)),
        "rows_before_first_broken": str(sum(is_hit(i) for i in range(min(broken)))),
    }
    ensure_distinct(spec, wrong)
    return spec, wrong


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
