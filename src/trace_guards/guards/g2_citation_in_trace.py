"""G2 citation_in_trace: cited document ids must have been retrieved in this run."""

from __future__ import annotations

from ..trace import Finding, Submission, ToolEvent, Trace

GUARD = "citation_in_trace"
SEPARATOR = " | "

_MSG_UNRETRIEVED = (
    "citation_in_trace: a cited document id was never returned by search_corpus "
    "or read_document in this run. Retrieve each document before citing it, or "
    "remove the citation."
)
_MSG_REQUIRED = (
    "citation_in_trace: this task needs a citation and none was given. Cite the "
    "id of a document retrieved in this run, or submit status cannot_determine."
)


def _line_id(line: str) -> str | None:
    head, sep, _ = line.partition(SEPARATOR)
    return head.strip() if sep else None


def retrieved_ids(event: ToolEvent) -> set[str]:
    """Ids in the id field of `id | title` lines; titles and body text are not ids."""
    lines = event.output.splitlines()
    if event.tool == "search_corpus":
        candidates = lines[1:]
    elif event.tool == "read_document":
        candidates = lines[:1]
    else:
        return set()
    return {i for i in map(_line_id, candidates) if i}


def check(
    trace: Trace, submission: Submission, *, requires_citation: bool = False
) -> list[Finding]:
    if submission.status == "cannot_determine":
        return []
    if not submission.citations:
        if requires_citation and submission.status == "answered":
            return [Finding(GUARD, _MSG_REQUIRED, {})]
        return []
    seen: set[str] = set()
    for event in trace.events:
        if not event.error:
            seen |= retrieved_ids(event)
    missing = [c for c in submission.citations if c not in seen]
    if not missing:
        return []
    return [Finding(GUARD, _MSG_UNRETRIEVED, {"unretrieved": missing})]
