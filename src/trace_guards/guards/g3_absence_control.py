"""G3 absence_control: an absence claim needs a lookup that is shown to find things."""

from __future__ import annotations

import json
import re

from ..trace import Finding, Submission, ToolEvent, Trace

GUARD = "absence_control"
LOOKUP_TOOLS = ("search_corpus", "search_annotations", "python")

_HITS_LINE = re.compile(r"hits: (\d+)")

_MSG_NO_LOOKUP = (
    "absence_control: an absence claim needs at least one lookup with a search "
    "tool or python that finished without error. Run a lookup first."
)
_MSG_NO_CONTROL = (
    "absence_control: one empty lookup does not show that the lookup can find "
    "anything. With the same tool, run a query that returns hits or try a "
    "different query, then submit again."
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


def _has_control(tool: str, events: list[ToolEvent]) -> bool:
    # python output has no declared hit format, so only distinct queries count.
    if tool != "python" and any(hit_count(e) > 0 for e in events):
        return True
    queries = {json.dumps(e.arguments, sort_keys=True, default=str) for e in events}
    return len(queries) >= 2


def check(
    trace: Trace, submission: Submission, *, requires_citation: bool = False
) -> list[Finding]:
    if submission.status != "absent":
        return []
    by_tool: dict[str, list[ToolEvent]] = {}
    for event in trace.events:
        if event.tool in LOOKUP_TOOLS and not event.error:
            by_tool.setdefault(event.tool, []).append(event)
    if not by_tool:
        return [Finding(GUARD, _MSG_NO_LOOKUP, {})]
    if any(_has_control(tool, events) for tool, events in by_tool.items()):
        return []
    counts = {tool: len(events) for tool, events in by_tool.items()}
    return [Finding(GUARD, _MSG_NO_CONTROL, {"clean_lookups": counts})]
