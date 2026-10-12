"""Run every labelled corpus case through its guard and compare with the label."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# The package is not installed in the test environment.
sys.path.insert(0, str(ROOT / "src"))

from trace_guards.guards import (  # noqa: E402
    g1_value_evidence,
    g2_citation_in_trace,
    g3_absence_control,
    g4_artifact_and_failure,
    g5_silent_discard,
    run_all,
)
from trace_guards.trace import submission_from_dict, trace_from_dict  # noqa: E402

CORPUS_DIR = ROOT / "tests" / "corpus"
MIN_PER_LABEL = 5
GUARDS = {
    "g1_value_evidence": g1_value_evidence,
    "g2_citation_in_trace": g2_citation_in_trace,
    "g3_absence_control": g3_absence_control,
    "g4_artifact_and_failure": g4_artifact_and_failure,
    "g5_silent_discard": g5_silent_discard,
}


def load(name: str) -> list[dict]:
    text = (CORPUS_DIR / f"{name}.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@pytest.mark.parametrize("name", sorted(GUARDS))
def test_corpus_matches_labels(name: str) -> None:
    guard = GUARDS[name]
    rows = load(name)
    counts = {"fire": 0, "pass": 0}
    mismatches = []
    for row in rows:
        assert row["label"] in counts, f"{row['id']}: unknown label {row['label']!r}"
        counts[row["label"]] += 1
        trace = trace_from_dict(row["trace"])
        submission = submission_from_dict(row["submission"])
        findings = guard.check(
            trace, submission, requires_citation=row["requires_citation"]
        )
        assert all(f.guard == guard.GUARD for f in findings)
        got = "fire" if findings else "pass"
        if got != row["label"]:
            mismatches.append(f"{row['id']}: label {row['label']}, got {got}")
    print(f"{name}: fire={counts['fire']} pass={counts['pass']} total={len(rows)}")
    # An empty or one-sided corpus checks nothing, so it must not pass.
    assert counts["fire"] >= MIN_PER_LABEL, f"{name}: too few fire cases {counts}"
    assert counts["pass"] >= MIN_PER_LABEL, f"{name}: too few pass cases {counts}"
    assert not mismatches, "\n".join(mismatches)


def test_cannot_determine_passes_every_guard() -> None:
    checked = 0
    for name in GUARDS:
        for row in load(name):
            if row["submission"]["status"] != "cannot_determine":
                continue
            checked += 1
            findings = run_all(
                trace_from_dict(row["trace"]),
                submission_from_dict(row["submission"]),
                requires_citation=True,
            )
            assert findings == [], row["id"]
    assert checked >= 4


def test_messages_carry_no_values() -> None:
    """Rejection text names the rule only; offending values stay in detail."""
    checked = 0
    for name, guard in GUARDS.items():
        for row in load(name):
            for finding in guard.check(
                trace_from_dict(row["trace"]),
                submission_from_dict(row["submission"]),
                requires_citation=row["requires_citation"],
            ):
                checked += 1
                assert not any(ch.isdigit() for ch in finding.message), row["id"]
    assert checked >= 4 * MIN_PER_LABEL
