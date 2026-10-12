"""G5: conservative detection of explicit discard operations in Python traces."""

from __future__ import annotations

import ast

from ..trace import Finding, Submission, Trace

GUARD = "silent_discard"
MESSAGE = (
    "silent_discard: Python source contains an operation that can silently "
    "discard data. This trace does not establish input completeness. "
    "Use status cannot_determine if the provided material cannot support an answer."
)


def operations(code: str) -> list[str]:
    """Recognize literal call syntax only; do not infer execution or data flow."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if (isinstance(function, ast.Name) and function.id == "dropna") or (
            isinstance(function, ast.Attribute) and function.attr == "dropna"
        ):
            found.add("dropna")
        for keyword in node.keywords:
            if not isinstance(keyword.value, ast.Constant):
                continue
            if keyword.arg == "errors" and keyword.value.value == "coerce":
                found.add("errors=coerce")
            if keyword.arg == "on_bad_lines" and keyword.value.value == "skip":
                found.add("on_bad_lines=skip")
    return sorted(found)


def check(
    trace: Trace, submission: Submission, *, requires_citation: bool = False
) -> list[Finding]:
    if submission.status == "cannot_determine":
        return []
    findings: list[Finding] = []
    for event in trace.events:
        code = event.arguments.get("code")
        if event.tool != "python" or event.error or not isinstance(code, str):
            continue
        risky = operations(code)
        if risky:
            findings.append(Finding(GUARD, MESSAGE, {"event": event.index, "operations": risky}))
    return findings
