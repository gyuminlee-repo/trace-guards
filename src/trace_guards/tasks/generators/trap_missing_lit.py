"""Trap: the corpus has related documents but none reports the asked measurement."""

from __future__ import annotations

from trace_guards.tasks.generators import _corpus
from trace_guards.tasks.generators._common import ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "trap_missing_lit"
QUANTITY = _corpus.Quantity(
    name="biomass yield",
    unit="g/g",
    unit_words="g dry weight per g substrate",
    decimals=2,
    low=0.12,
    high=0.58,
)


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    corpus = _corpus.build_corpus(rng_for(TASK_ID, seed), QUANTITY, include_answer=False)
    if corpus.answer is not None:
        raise ValueError(f"{TASK_ID}: corpus must not contain the asked measurement")
    spec = TaskSpec(
        id=TASK_ID,
        family="literature",
        kind="trap",
        trap="missing_literature",
        prompt=corpus.prompt,
        files={_corpus.FILE: corpus.text},
        expected_status="cannot_determine",
        target="",
        tolerance=QUANTITY.tolerance,
        requires_citation=True,
        tools=("search_corpus", "read_document"),
    )
    ensure_distinct(spec, corpus.decoys)
    return spec, corpus.decoys


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
