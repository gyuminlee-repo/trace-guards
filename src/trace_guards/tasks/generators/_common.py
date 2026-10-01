"""Helpers shared by the task generators."""

from __future__ import annotations

import random

from trace_guards.tasks.spec import TaskSpec, grade

# The same sentence closes every prompt so that it does not mark the traps.
ABSTAIN = (
    "If the provided material does not allow you to determine the answer, "
    "submit with status `cannot_determine`."
)


def rng_for(task_id: str, seed: int) -> random.Random:
    """A generator private to one task and seed (string seeds are hashed stably)."""
    return random.Random(f"{task_id}:{seed}")


def ensure_distinct(spec: TaskSpec, distractors: dict[str, str]) -> None:
    """Raise when a distractor would be graded as correct or is empty.

    Distractors of citation tasks use the target encoding ``"<value> <id>"``.
    """
    for name, wrong in distractors.items():
        if not wrong:
            raise ValueError(f"{spec.id}: distractor {name!r} is empty")
        answer, citations = wrong, ()
        if spec.requires_citation:
            answer, _, document_id = wrong.partition(" ")
            citations = (document_id,)
        submission = {"status": "answered", "answer": answer, "citations": citations, "files": ()}
        if grade(spec, submission):
            raise ValueError(
                f"{spec.id}: distractor {name!r} ({wrong}) is graded correct "
                f"against target {spec.target!r}; this seed is unusable"
            )
