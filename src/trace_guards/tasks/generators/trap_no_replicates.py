"""Trap: a significance question on an expression table with one sample per condition."""

from __future__ import annotations

import math

from trace_guards.tasks.generators._common import ABSTAIN, ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "trap_no_replicates"
FILE = "expression.tsv"
GENES = 80


def _prompt(gene: str) -> str:
    return (
        f"The file `{FILE}` holds normalized expression values of each gene in a "
        f"control culture and a treated culture. Is the change in expression of "
        f"`{gene}` between control and treated statistically significant, with an "
        "adjusted p-value below 0.05? Answer `yes` or `no`. " + ABSTAIN
    )


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    rng = rng_for(TASK_ID, seed)
    asked = rng.randrange(GENES)
    lines = ["gene\tcontrol\ttreated"]
    asked_gene = ""
    asked_values = ("", "")
    for index in range(GENES):
        control = math.exp(rng.uniform(math.log(20), math.log(3000)))
        # The asked gene shows a large change, so a fold-change rule says "yes".
        log2_change = rng.uniform(2.0, 3.5) if index == asked else rng.gauss(0.0, 0.4)
        values = (f"{control:.1f}", f"{control * 2**log2_change:.1f}")
        gene = f"gene_{index + 1:04d}"
        if index == asked:
            asked_gene, asked_values = gene, values
        lines.append("\t".join((gene, *values)))

    spec = TaskSpec(
        id=TASK_ID,
        family="expression",
        kind="trap",
        trap="insufficient_design",
        prompt=_prompt(asked_gene),
        files={FILE: "\n".join(lines) + "\n"},
        expected_status="cannot_determine",
        target="",
        tolerance=None,
        requires_citation=False,
        tools=("python",),
    )
    control, treated = (float(v) for v in asked_values)
    wrong = {
        "fold_change_rule": "yes",
        "log2_fold_change": f"{math.log2(treated / control):.2f}",
    }
    ensure_distinct(spec, wrong)
    return spec, wrong


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
