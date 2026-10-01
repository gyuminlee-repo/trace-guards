"""G4 artifact_and_failure: declared files exist; no answer on top of a failed run."""

from __future__ import annotations

import posixpath

from ..trace import Finding, Submission, Trace

GUARD = "artifact_and_failure"

_MSG_FILE = (
    "artifact_and_failure: a file listed in files is missing from the working "
    "directory or is empty. Write the file, check that it has content, then "
    "submit again, or leave it out of files."
)
_MSG_FAILURE = (
    "artifact_and_failure: the last python call ended with an error and no tool "
    "call succeeded after it. Fix the error and rerun before submitting an "
    "answer, or submit status cannot_determine."
)


def check(
    trace: Trace, submission: Submission, *, requires_citation: bool = False
) -> list[Finding]:
    # Section 5: honest abstention is never blocked, so this status is exempt
    # although section 6 says the guard applies always.
    if submission.status == "cannot_determine":
        return []
    findings: list[Finding] = []

    sizes = {posixpath.normpath(p): n for p, n in trace.workdir_files.items()}
    bad = [p for p in submission.files if sizes.get(posixpath.normpath(p), 0) == 0]
    if bad:
        findings.append(Finding(GUARD, _MSG_FILE, {"missing_or_empty": bad}))

    if submission.status == "answered":
        python_events = [e for e in trace.events if e.tool == "python"]
        if python_events and python_events[-1].error:
            last = python_events[-1].index
            if not any(e.index > last and not e.error for e in trace.events):
                findings.append(Finding(GUARD, _MSG_FAILURE, {"event": last}))
    return findings
