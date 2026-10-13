"""Deterministic evidence guards. Standard library only; no model call, no network."""

from __future__ import annotations

from dataclasses import dataclass

from ..trace import Finding, Submission, Trace
from . import (
    g1_value_evidence,
    g2_citation_in_trace,
    g3_absence_control,
    g4_artifact_and_failure,
    g5_silent_discard,
)

GUARDS = (
    g1_value_evidence,
    g2_citation_in_trace,
    g3_absence_control,
    g4_artifact_and_failure,
)

DEFAULT_MAX_REJECTIONS = 2
VERSIONS = ("v0", "v1")


def run_all(
    trace: Trace, submission: Submission, *, requires_citation: bool = False,
    guard_version: str = "v0",
) -> list[Finding]:
    if guard_version not in VERSIONS:
        raise ValueError(f"unknown guard version: {guard_version}")
    findings: list[Finding] = []
    guards = GUARDS + (g5_silent_discard,) if guard_version == "v1" else GUARDS
    for guard in guards:
        findings.extend(
            guard.check(trace, submission, requires_citation=requires_citation)
        )
    return findings


@dataclass(frozen=True)
class GateDecision:
    accept: bool
    exhausted: bool
    message: str


def rejection_message(findings: list[Finding]) -> str:
    lines = ["Submission rejected. Nothing was submitted."]
    lines.extend(f"- {f.message}" for f in findings)
    return "\n".join(lines)


def gate_decision(
    findings: list[Finding],
    prior_rejections: int,
    max_rejections: int = DEFAULT_MAX_REJECTIONS,
) -> GateDecision:
    """Decide on one submission given the findings and the rejections so far."""
    if not findings:
        return GateDecision(accept=True, exhausted=False, message="")
    if prior_rejections >= max_rejections:
        return GateDecision(accept=True, exhausted=True, message="")
    return GateDecision(
        accept=False, exhausted=False, message=rejection_message(findings)
    )
