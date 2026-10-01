"""Literature lookup: exactly one corpus document reports the asked measurement."""

from __future__ import annotations

from trace_guards.tasks.generators import _corpus
from trace_guards.tasks.generators._common import ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "lit_lookup"
QUANTITY = _corpus.Quantity(
    name="doubling time", unit="h", unit_words="hours", decimals=1, low=0.8, high=9.5
)


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    corpus = _corpus.build_corpus(rng_for(TASK_ID, seed), QUANTITY, include_answer=True)
    if corpus.answer is None:
        raise ValueError(f"{TASK_ID}: corpus was built without the answer document")
    spec = TaskSpec(
        id=TASK_ID,
        family="literature",
        kind="ordinary",
        trap=None,
        prompt=corpus.prompt,
        files={_corpus.FILE: corpus.text},
        expected_status="answered",
        target=corpus.answer,
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
