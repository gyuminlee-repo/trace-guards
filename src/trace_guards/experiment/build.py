"""Build one Inspect task from a TaskSpec and a condition (DESIGN.md section 10).

The two conditions differ only in the body of the submit tool. The agent
prompt is the Inspect ReAct default in both, the tool list comes from the
spec, and the submit tool has one name and one description.
"""

from __future__ import annotations

from typing import Any, Mapping

from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer
from inspect_ai.solver import TaskState
from inspect_ai.tool import Tool

from .. import inspect_adapter as ia
from ..tasks.spec import TaskSpec, grade

CONDITIONS = ("gate_off", "gate_on")
MESSAGE_LIMIT = 30
TEMPERATURE = 0.7
MAX_REJECTIONS = 2
SCORER_NAME = "accepted_submission"

TOOL_FACTORIES = {
    "python": ia.recorded_python,
    "search_corpus": ia.search_corpus,
    "read_document": ia.read_document,
    "search_annotations": ia.search_annotations,
}


def tools_for(spec: TaskSpec) -> list[Tool]:
    """The tools the spec offers, in spec order. Raises KeyError for an unknown name."""
    return [TOOL_FACTORIES[name]() for name in spec.tools]


def accepted_record(data: Mapping[str, Any]) -> dict | None:
    """The last accepted submission record of one run, or None."""
    accepted = [r for r in ia.submissions_in(data) if r["accepted"]]
    return accepted[-1] if accepted else None


def grade_store(spec: TaskSpec, data: Mapping[str, Any]) -> tuple[bool, str]:
    """Grade the last accepted submission in a sample store: (correct, reason)."""
    record = accepted_record(data)
    if record is None:
        calls = len(ia.submissions_in(data))
        return False, f"no accepted submission ({calls} submit calls, all rejected or none made)"
    correct = grade(spec, record["submission"])
    return correct, "graded the last accepted submission"


@scorer(metrics=[accuracy()], name=SCORER_NAME)
def accepted_submission(spec: TaskSpec) -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        correct, reason = grade_store(spec, state.store)
        record = accepted_record(state.store)
        return Score(
            value=CORRECT if correct else INCORRECT,
            answer=None if record is None else record["submission"]["answer"],
            explanation=reason,
            metadata={"accepted_submission_present": record is not None},
        )

    return score


def build_task(spec: TaskSpec, condition: str) -> Task:
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}, got {condition!r}")
    sample = Sample(
        id=spec.id,
        input=spec.prompt,
        files=dict(spec.files),
        metadata={
            "requires_citation": spec.requires_citation,
            "kind": spec.kind,
            "trap": spec.trap,
            "expected_status": spec.expected_status,
        },
    )
    return Task(
        name=f"{spec.id}_{condition}",
        dataset=[sample],
        solver=[
            ia.trace_setup(),
            react(
                tools=tools_for(spec),
                submit=ia.agent_submit(condition == "gate_on", MAX_REJECTIONS),
            ),
        ],
        scorer=accepted_submission(spec),
        sandbox="local",
        message_limit=MESSAGE_LIMIT,
        config=GenerateConfig(temperature=TEMPERATURE),
        metadata={"task_id": spec.id, "condition": condition},
    )
