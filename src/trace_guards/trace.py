"""Framework-neutral record of one agent run (DESIGN.md section 4)."""

from __future__ import annotations

from dataclasses import dataclass, field

STATUSES = ("answered", "absent", "cannot_determine")


@dataclass(frozen=True)
class ToolEvent:
    index: int
    tool: str
    arguments: dict
    output: str
    error: bool


@dataclass(frozen=True)
class Submission:
    status: str
    answer: str
    citations: tuple[str, ...] = ()
    files: tuple[str, ...] = ()


@dataclass(frozen=True)
class Trace:
    task_id: str
    prompt: str
    events: tuple[ToolEvent, ...]
    workdir_files: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    guard: str
    message: str
    detail: dict


def submission_from_dict(data: dict) -> Submission:
    return Submission(
        status=data["status"],
        answer=data["answer"],
        citations=tuple(data["citations"]),
        files=tuple(data["files"]),
    )


def trace_from_dict(data: dict) -> Trace:
    events = tuple(
        ToolEvent(
            index=i,
            tool=e["tool"],
            arguments=dict(e["arguments"]),
            output=e["output"],
            error=bool(e["error"]),
        )
        for i, e in enumerate(data["events"])
    )
    return Trace(
        task_id=data["task_id"],
        prompt=data["prompt"],
        events=events,
        workdir_files=dict(data["workdir_files"]),
    )
