"""G3 absence_control: an empty search supports an absence claim only with a positive control.

A claim that rests on python alone is not judged: python output has no
declared hit count, so there is nothing structured to read and it passes.
python events never count as the empty lookup or as the control of a search.
"""

from __future__ import annotations

import re

from ..trace import Finding, Submission, ToolEvent, Trace

GUARD = "absence_control"
SEARCH_TOOLS = ("search_corpus", "search_annotations")

_HITS_LINE = re.compile(r"hits: (\d+)")

_MSG_NO_LOOKUP = (
    "absence_control: an absence claim needs a lookup that finished without "
    "error. This run has none."
)
_MSG_NO_CLEAN_SEARCH = (
    "absence_control: every search in this run ended with an error, so no "
    "search supports the absence claim."
)
_MSG_NO_EMPTY = (
    "absence_control: an absence claim needs a search that came back with zero "
    "hits. No search in this run came back empty."
)
_MSG_NO_CONTROL = (
    "absence_control: a search with zero hits is evidence of absence only when "
    "the same search tool has found an existing item in this run. It has not, "
    "so the empty search does not support the claim."
)


def hit_count(event: ToolEvent) -> int:
    """Hit count declared on the first output line of a search_* tool."""
    first = event.output.split("\n", 1)[0]
    match = _HITS_LINE.fullmatch(first.strip())
    if match is None:
        raise ValueError(
            f"{event.tool} event {event.index}: first output line is not 'hits: N'"
        )
    return int(match.group(1))


def check(
    trace: Trace, submission: Submission, *, requires_citation: bool = False
) -> list[Finding]:
    if submission.status != "absent":
        return []
    searches = [e for e in trace.events if e.tool in SEARCH_TOOLS]
    if not searches:
        if any(e.tool == "python" and not e.error for e in trace.events):
            return []  # python only: not judged
        return [Finding(GUARD, _MSG_NO_LOOKUP, {})]

    # Per search tool: hit counts of its calls that finished without error.
    counts: dict[str, list[int]] = {}
    for event in searches:
        if not event.error:
            counts.setdefault(event.tool, []).append(hit_count(event))
    if not counts:
        return [Finding(GUARD, _MSG_NO_CLEAN_SEARCH, {})]
    # The empty search and its control must come from the same tool.
    with_empty = [tool for tool, hits in counts.items() if 0 in hits]
    if any(max(counts[tool]) > 0 for tool in with_empty):
        return []
    message = _MSG_NO_CONTROL if with_empty else _MSG_NO_EMPTY
    return [Finding(GUARD, message, {"hit_counts": counts})]
